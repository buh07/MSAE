#!/usr/bin/env python3
"""NORSPAN-1 source/history gates and isolated blind-payload builder.

This program is deliberately standard-library-only.  It never imports a model,
tokenizer, Torch, CUDA, or a training launcher.
"""
from __future__ import annotations

import msae_jumbo_pair_commit as jumbo_pair
import msae_norspan_jpc_runtime as jpc_runtime

import argparse
import contextlib
import contextvars
import msae_norspan_jpc_controls as jpc_controls
import msae_norspan_jpc_authority as jpc_authority
import collections
import codecs
import csv
import dataclasses
import errno
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import stat
import sys
import tarfile
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/msae_independent_norspan_v1/protocol.json"
PROV = ROOT / "reports/provenance/msae_independent_norspan_v1"
DATA = ROOT / "data/msae_independent_norspan_v1"
COMMIT = "396d11f0c2bd290a2a2711015c04ac25bc3dcc06"
REPO = "https://github.com/UniversalDependencies/UD_Norwegian-Bokmaal.git"
RAW = DATA / "raw" / COMMIT
PRIVATE = DATA / "private"
SOURCE_FILES = {
    "train": "no_bokmaal-ud-train.conllu",
    "dev": "no_bokmaal-ud-dev.conllu",
    "test": "no_bokmaal-ud-test.conllu",
}
LICENSE_FILE = "LICENSE.txt"
LEX = re.compile(r"[^\W_]+", re.UNICODE)
LICENSE_ID = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9]*(?:[.-][A-Za-z0-9]+)*)(?![A-Za-z0-9])")
UPOS = frozenset("ADJ ADP ADV AUX CCONJ DET INTJ NOUN NUM PART PRON PROPN PUNCT SCONJ SYM VERB X".split())
DEPREL = frozenset(
    "acl advcl advmod amod appos aux case cc ccomp clf compound conj cop csubj dep det "
    "discourse dislocated expl fixed flat goeswith iobj list mark nmod nsubj nummod obj "
    "obl orphan parataxis punct reparandum root vocative xcomp".split()
)
NUMBER = frozenset("Sing Plur Dual Trial Pauc Grpa Grpl Inv Ptan".split())
TASKS = (
    "absolute_bucket", "relative_quartile", "token_identity", "lemma_identity",
    "capitalization", "word_length", "punctuation", "sentence_boundary",
    "head_signed_distance", "dependency_depth", "upos_coarse", "deprel_coarse", "number",
)
REQUIRED = frozenset(
    "absolute_bucket relative_quartile capitalization word_length punctuation "
    "sentence_boundary head_signed_distance upos_coarse".split()
)
OPTIONAL = frozenset("dependency_depth deprel_coarse number token_identity lemma_identity".split())
QUARANTINES = {
    "data/atlas_v1/private/final.jsonl",
    "data/atlas_v1/private/final.records.jsonl",
    "data/atlas_v1/private/final.units.jsonl",
}
EXCLUDED_PREFIXES = (
    ".git/", ".cache/", ".venv-atlas/", ".pytest_cache/", ".generated/",
    "data/msae_independent_source_v8/", "data/msae_independent_source_v9/",
    "data/msae_independent_source_v10/", "data/msae_independent_norspan_v1/",
)
MODEL_SUFFIXES = frozenset(
    ".pt .pth .bin .safetensors .npy .npz .parquet .feather .orc .fits .so .a .pyc .pkl".split()
)
CAPABILITY_PROCESS_TOKENS = (
    "nvidia-smi", "torchrun", "accelerate", "deepspeed", "train", "training",
    "score", "scoring", "evaluate", "evaluation", "inference", "vllm", "tmux",
)
CAPABILITY_ENV_KEYS = (
    "CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES", "LOCAL_RANK", "RANK",
    "WORLD_SIZE", "TMUX",
)
TEXT_SUFFIXES = frozenset(
    ".txt .md .py .json .jsonl .csv .tsv .toml .yaml .yml .ini .cfg .log .tex .html .sh .lock .conllu".split()
)
ALLOWED_AUTHORITY_PATHS = frozenset({
    "docs/plan-msae-independent-norspan-v1.md",
    "reports/adversarial/msae_independent_norspan_v1_plan_review.md",
    "configs/msae_independent_norspan_v1/protocol.json",
    "scripts/prepare_msae_independent_norspan_v1.py",
    "scripts/acquire_msae_independent_norspan_v1.py",
    "tests/test_prepare_msae_independent_norspan_v1.py",
    "reports/verification/msae_independent_norspan_v1_source_free_checks.log",
    "reports/adversarial/msae_independent_norspan_v1_implementation_review.md",
    "reports/provenance/msae_independent_norspan_v1/current_history_registry.json",
    "reports/provenance/msae_independent_norspan_v1/baseline.json",
    "reports/provenance/msae_independent_norspan_v1/authority.json",
    "reports/adversarial/msae_independent_norspan_v1_authority_review.md",
    "reports/provenance/msae_independent_norspan_v1/acquisition_entry.json",
    "reports/provenance/msae_independent_norspan_v1/pre_network_ready.json",
    "reports/provenance/msae_independent_norspan_v1/network_started.json",
    "reports/provenance/msae_independent_norspan_v1/source_acquisition.json",
    "reports/provenance/msae_independent_norspan_v1/scientific_entry.json",
    "reports/provenance/msae_independent_norspan_v1/pre_raw_ready.json",
    "reports/provenance/msae_independent_norspan_v1/raw_access_started.json",
})
AUTHORITY_CONTROL_MODES = {
    "docs/plan-msae-independent-norspan-v1.md": 0o644,
    "reports/adversarial/msae_independent_norspan_v1_plan_review.md": 0o644,
    "configs/msae_independent_norspan_v1/protocol.json": 0o644,
    "scripts/prepare_msae_independent_norspan_v1.py": 0o755,
    "scripts/acquire_msae_independent_norspan_v1.py": 0o755,
    "tests/test_prepare_msae_independent_norspan_v1.py": 0o644,
    "reports/verification/msae_independent_norspan_v1_source_free_checks.log": 0o644,
    "reports/adversarial/msae_independent_norspan_v1_implementation_review.md": 0o644,
    "reports/provenance/msae_independent_norspan_v1/current_history_registry.json": 0o644,
    "reports/provenance/msae_independent_norspan_v1/baseline.json": 0o644,
}
LEGACY_AUTHORITY_CONTROL_MODES = dict(AUTHORITY_CONTROL_MODES)
AUTHORITY_CONTROL_MODES.update(jpc_authority.INTEGRATION_MODES)
ALLOWED_AUTHORITY_PATHS = ALLOWED_AUTHORITY_PATHS | frozenset(jpc_authority.INTEGRATION_MODES)
ALIAS_SEQUENCES = (
    ("ud", "norwegian", "bokmaal"), ("norwegian", "bokmaal"), ("no", "bokmaal"),
    ("https", "github", "com", "universaldependencies", "ud", "norwegian", "bokmaal", "git"),
    ("https", "github", "com", "universaldependencies", "ud", "norwegian", "bokmaal"),
    (COMMIT,),
    ("no", "bokmaal", "ud", "train", "conllu"),
    ("no", "bokmaal", "ud", "train"),
    ("no", "bokmaal", "ud", "dev", "conllu"),
    ("no", "bokmaal", "ud", "dev"),
    ("no", "bokmaal", "ud", "test", "conllu"),
    ("no", "bokmaal", "ud", "test"),
    ("license", "txt"), ("license",),
)
SCIENCE_PREFIX = (
    "source_manifest.json", "license.json", "candidate_pedigree.json", "dedup.json",
    "history_overlap.json", "internal_overlap_prune.json", "role_manifest.json",
    "cross_role_overlap.json", "support.json",
)
PHASE_PUBLIC = {
    "current_history_registry.json", "baseline.json", "authority.json",
    "acquisition_entry.json", "pre_network_ready.json", "network_started.json",
    "source_acquisition.json", "scientific_entry.json", "pre_raw_ready.json",
    "raw_access_started.json", *SCIENCE_PREFIX, "source_ready.json",
    "no_training_gate.json", "seal.json", "rejection.json",
}


class GateFailure(RuntimeError):
    """First fail-closed protocol gate."""

class ScientificGateFailure(GateFailure):
    """A deterministic source-format/gate rejection, not an IO/custody failure."""
    pass


@dataclasses.dataclass(frozen=True)
class Token:
    id: int
    form: str
    lemma: str
    upos: str
    feats: str
    head: int
    deprel: str


@dataclasses.dataclass(frozen=True)
class Sentence:
    partition: str
    sent_id: str
    group_key: tuple[str, str]
    tokens: tuple[Token, ...]
    source_index: int


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")



_PAIR_SESSION = contextvars.ContextVar("norspan_outside_expected_controls", default=None)


@contextlib.contextmanager
def paired_control_session(session):
    if not isinstance(session, jpc_controls.ControlSession) or session.root != PROV:
        raise GateFailure("paired_control_session_root")
    token = _PAIR_SESSION.set(session)
    try:
        yield session
    finally:
        _PAIR_SESSION.reset(token)


def _paired_control_name(path):
    # Only finite prescribed logical public controls, NEVER ordinary code/history.
    if path.parent == PROV and path.name in PHASE_PUBLIC:
        return path.name
    return None


def _expected_session():
    session = _PAIR_SESSION.get()
    if session is None:
        raise GateFailure("paired_control_session_required")
    return session


def canonical_implementation_review_path():
    # Older retained BLOCK/SHIP reports are ordinary history. No implicit SHIP
    # filename/first-line fallback may become the new implementation authority.
    approval = _expected_session().authority
    if approval is None:
        raise GateFailure("outside_canonical_whole_binding_pending")
    return approval.verify_release()


def canonical_authority_review_path():
    session = _expected_session()
    if session.authority is None:
        raise GateFailure("authenticated_source_authority_pending")
    return session.authority.verify_authority(session)

def review_is_ship(path: Path) -> bool:
    try:
        text = read_bytes_nofollow(path, mode=0o644, nlink=1).decode("utf-8", "strict")
    except (UnicodeDecodeError, FileNotFoundError):
        return False
    return text.splitlines()[:1] == ["VERDICT: SHIP"]


def canonical_file_bytes(value: Any) -> bytes:
    return canonical_bytes(value) + b"\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stream_file_digest(path: Path, *, mode: int | None = None, nlink: int | None = None,
                       expected: os.stat_result | tuple[int, int, int, int, int, int] | None = None,
                       max_bytes: int = jpc_runtime.FILE_BYTES_LIMIT) -> dict[str, Any]:
    _reader_fd_admission(path)
    control = _paired_control_name(path)
    if control is not None:
        item = _expected_session().digest(control)
        if (mode is not None and mode != item["mode"] or nlink is not None and nlink != 2
                or item["bytes"] > max_bytes):
            raise GateFailure("paired_control_digest_limits")
        if expected is not None and isinstance(expected, os.stat_result):
            receipt = _expected_session().expected(control)
            if (expected.st_dev, expected.st_ino) != (receipt.device, receipt.inode):
                raise GateFailure("paired_control_identity_drift")
        return {"sha256":item["sha256"],"bytes":item["bytes"],"record_count":1}
    if nlink is None:
        nlink = 1
    if type(max_bytes) is not int or not 1 <= max_bytes <= jpc_runtime.FILE_BYTES_LIMIT:
        raise GateFailure("digest_limit_schema")
    h = hashlib.sha256()
    parent_fd = _open_parent_fd(path)
    fd = -1
    primary = None
    try:
        _validate_parent_fd(parent_fd)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise GateFailure("not_regular:" + path.as_posix())
        if mode is not None and stat.S_IMODE(before.st_mode) != mode:
            raise GateFailure("wrong_mode:" + path.as_posix())
        if nlink is not None and before.st_nlink != nlink:
            raise GateFailure("wrong_nlink:" + path.as_posix())
        expected_identity = _identity(expected) if isinstance(expected, os.stat_result) else expected
        if expected_identity is not None and _identity(before) != expected_identity:
            raise GateFailure("file_identity_drift:" + path.as_posix())
        if before.st_size > max_bytes:
            raise GateFailure("file_too_large:" + path.as_posix())
        total = records = 0
        while block := os.read(fd, min(1024 * 1024, max_bytes - total + 1)):
            h.update(block)
            total += len(block)
            if total > max_bytes:
                raise GateFailure("file_too_large:" + path.as_posix())
            records += block.count(b"\n")
        after = os.fstat(fd)
        current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        _validate_parent_fd(parent_fd)
        if jumbo_pair._fingerprint(before) != jumbo_pair._fingerprint(after) or jumbo_pair._fingerprint(after) != jumbo_pair._fingerprint(current):
            raise GateFailure("file_identity_drift:" + path.as_posix())
    except BaseException as exc:
        primary = exc
        raise
    finally:
        _finish_reader(parent_fd, fd, primary)
    return {"sha256": h.hexdigest(), "bytes": total, "record_count": records}


def sha_file(path: Path, expected: os.stat_result | tuple[int, int, int, int, int, int] | None = None) -> str:
    return stream_file_digest(path, expected=expected)["sha256"]


def create_directory_exclusive(path: Path, mode: int) -> None:
    parent = _open_parent_fd(path, create=True)
    fd = -1
    primary = None
    try:
        try:
            os.mkdir(path.name, 0o700, dir_fd=parent)
        except FileExistsError as exc:
            raise GateFailure("directory_create_once:" + path.as_posix()) from exc
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        if _identity(os.fstat(fd))[:3] != _identity(before)[:3]:
            raise GateFailure("directory_identity_drift")
        os.fchmod(fd, mode)
        current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if _identity(current)[:4] != _identity(os.fstat(fd))[:4]:
            raise GateFailure("directory_identity_drift")
        os.fsync(fd); os.fsync(parent)
        _validate_parent_fd(parent)
    except BaseException as exc:
        primary = exc
        raise
    finally:
        _finish_reader(parent, fd, primary)


def _identity(st: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (st.st_dev, st.st_ino, stat.S_IFMT(st.st_mode), stat.S_IMODE(st.st_mode),
            st.st_nlink, st.st_size)


def _relative_to_root(path: Path) -> tuple[str, ...]:
    try:
        rel = path.resolve(strict=False).relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise GateFailure("path_outside_root:" + path.as_posix()) from exc
    if any(part in {"", ".", ".."} for part in rel.parts):
        raise GateFailure("invalid_relative_path")
    return rel.parts


class _PinnedParent(int):
    """Leaf fd plus every retained named ancestor; caller must close the chain."""
    def __new__(cls, descriptors: list[int], links: list[tuple[int, str, int, tuple[int, ...]]]):
        obj = int.__new__(cls, descriptors[-1])
        obj.descriptors = descriptors
        obj.links = links
        obj.root_identity = _identity(os.fstat(descriptors[0]))[:4]
        return obj


def _validate_parent_fd(fd: int) -> None:
    # Plain caller-owned leaf descriptors are guarded by their enclosing loader.
    if not isinstance(fd, _PinnedParent):
        return
    if (_identity(os.fstat(fd.descriptors[0]))[:4] != fd.root_identity
            or _identity(os.stat("/", follow_symlinks=False))[:4] != fd.root_identity):
        raise GateFailure("parent_chain_root_drift")
    for parent, name, child, expected in fd.links:
        try:
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise GateFailure("parent_chain_drift:" + name) from exc
        if (_identity(named)[:4] != expected
                or _identity(os.fstat(child))[:4] != expected):
            raise GateFailure("parent_chain_drift:" + name)


def _close_parent_fd(fd: int, *, primary: BaseException | None = None) -> None:
    descriptors = fd.descriptors if isinstance(fd, _PinnedParent) else [fd]
    jumbo_pair._close_fds(reversed(descriptors), primary=primary)



def _finish_reader(parent, fd, primary, *, owns_parent=True):
    # This module's PinnedParent is NOT the primitive's PinnedParent class.
    descriptors = ([] if fd is None or fd < 0 else [fd])
    if owns_parent:
        descriptors += list(reversed(parent.descriptors)) if isinstance(parent, _PinnedParent) else [parent]
    jumbo_pair._close_fds(descriptors, primary=primary)

def _reader_fd_admission(path: Path) -> None:
    """Conservative controlled-caller admission, not a kernel FD quota.

    A reader retains '/' and every absolute parent plus a leaf. len(parts)
    covers that chain; eight additional slots cover a newly retained census
    child, its active scandir/monitor and paired-reader transients. Current
    count includes all held originals and unrelated caller descriptors.
    """
    absolute = path if path.is_absolute() else ROOT / path
    if '.msae_keys' in absolute.parts:
        raise GateFailure('history_credential_namespace_prohibited')
    if jpc_runtime._current_fd_count() + len(absolute.parts) + 8 > 4096:
        raise GateFailure('history_fd_admission')


def _open_parent_fd(path: Path, *, create: bool = False, mode: int = 0o755) -> int:
    """Retain and revalidate the complete absolute no-follow ancestor chain."""
    absolute = path if path.is_absolute() else ROOT / path
    parts = absolute.parts[1:]
    if '.msae_keys' in parts:
        raise GateFailure('history_credential_namespace_prohibited')
    if any(part in {"", ".", ".."} for part in parts):
        raise GateFailure("invalid_relative_path")
    _reader_fd_admission(absolute)
    descriptors = [os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)]
    links = []
    try:
        for part in parts[:-1]:
            parent = descriptors[-1]
            try:
                before = os.stat(part, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode, dir_fd=parent)
                os.fsync(parent)
                before = os.stat(part, dir_fd=parent, follow_symlinks=False)
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            descriptors.append(child)
            expected = _identity(before)[:4]
            if _identity(os.fstat(child))[:4] != expected:
                raise GateFailure("parent_chain_drift:" + part)
            links.append((parent, part, child, expected))
        pinned = _PinnedParent(descriptors, links)
        _validate_parent_fd(pinned)
        return pinned
    except BaseException as exc:
        jumbo_pair._close_fds(reversed(descriptors), primary=exc)
        raise


def ensure_directory(path: Path, mode: int) -> None:
    parent = _open_parent_fd(path, create=True, mode=mode)
    fd = None
    primary = None
    try:
        created = False
        try:
            os.mkdir(path.name, mode, dir_fd=parent)
            created = True
            os.fsync(parent)
        except FileExistsError:
            pass
        fd = os.open(path.name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                     | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent)
        if created:
            os.fchmod(fd, mode)
            os.fsync(fd); os.fsync(parent)
        st = os.fstat(fd)
        current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if _identity(st)[:4] != _identity(current)[:4] or stat.S_IMODE(st.st_mode) != mode:
            raise GateFailure("directory_metadata:" + path.as_posix())
        _validate_parent_fd(parent)
    except BaseException as exc:
        primary = exc
        raise
    finally:
        descriptors = ([] if fd is None else [fd]) + list(reversed(parent.descriptors))
        jumbo_pair._close_fds(descriptors, primary=primary)


def publish_flat_directory(path: Path, files: dict[str, bytes], *,
                           directory_mode: int, file_mode: int) -> dict[str, dict[str, Any]]:
    """Retained-owned JPC aggregate. Whole state/schema integration is pending."""
    _relative_to_root(path)
    ensure_directory(path.parent, 0o700)
    manifest = jpc_runtime.publish_flat_pairs(path, files, directory_mode=directory_mode,
                                             file_mode=file_mode)
    session = _PAIR_SESSION.get()
    if session is not None and path == RAW:
        session.raw_manifest = manifest
        session.checkpoint()
    return manifest


def read_bytes_nofollow(path: Path, *, mode: int | None = None,
                        nlink: int | None = None, max_bytes: int | None = None,
                        expected: os.stat_result | tuple[int, int, int, int, int, int] | None = None,
                        parent_fd: int | None = None) -> bytes:
    _reader_fd_admission(path)
    control = _paired_control_name(path)
    if control is not None:
        if parent_fd is not None or nlink not in {None, 2} or mode not in {None, 0o644}:
            raise GateFailure("paired_control_read_parameters")
        return _expected_session().read(control, max_bytes=jpc_runtime.FILE_BYTES_LIMIT if max_bytes is None else max_bytes)
    if nlink is None:
        nlink = 1
    if max_bytes is None:
        max_bytes = jpc_runtime.FILE_BYTES_LIMIT
    if type(max_bytes) is not int or not 1 <= max_bytes <= jpc_runtime.FILE_BYTES_LIMIT:
        raise GateFailure("read_limit_schema")
    owns_parent = parent_fd is None
    if parent_fd is None:
        parent_fd = _open_parent_fd(path)
    fd = -1
    primary = None
    try:
        _validate_parent_fd(parent_fd)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise GateFailure("not_regular:" + path.as_posix())
        if mode is not None and stat.S_IMODE(before.st_mode) != mode:
            raise GateFailure("wrong_mode:" + path.as_posix())
        if nlink is not None and before.st_nlink != nlink:
            raise GateFailure("wrong_nlink:" + path.as_posix())
        if max_bytes is not None and before.st_size > max_bytes:
            raise GateFailure("file_too_large:" + path.as_posix())
        expected_identity = _identity(expected) if isinstance(expected, os.stat_result) else expected
        if expected_identity is not None and _identity(before) != expected_identity:
            raise GateFailure("file_identity_drift:" + path.as_posix())
        chunks: list[bytes] = []
        total = 0
        while block := os.read(fd, min(1024 * 1024, max_bytes - total + 1)):
            total += len(block)
            if max_bytes is not None and total > max_bytes:
                raise GateFailure("file_too_large:" + path.as_posix())
            chunks.append(block)
        after = os.fstat(fd)
        current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        _validate_parent_fd(parent_fd)
        if jumbo_pair._fingerprint(before) != jumbo_pair._fingerprint(after) or jumbo_pair._fingerprint(after) != jumbo_pair._fingerprint(current):
            raise GateFailure("file_identity_drift:" + path.as_posix())
        return b"".join(chunks)
    except BaseException as exc:
        primary = exc
        raise
    finally:
        _finish_reader(parent_fd, fd, primary, owns_parent=owns_parent)


def read_prefix_nofollow(path: Path, limit: int,
                         expected: os.stat_result | tuple[int, int, int, int, int, int] | None = None) -> bytes:
    if type(limit) is not int or not 1 <= limit <= jpc_runtime.FILE_BYTES_LIMIT:
        raise GateFailure("prefix_limit_schema")
    _reader_fd_admission(path)
    control = _paired_control_name(path)
    if control is not None:
        return _expected_session().read_prefix(control, limit=limit)
    parent_fd = _open_parent_fd(path)
    fd = -1
    primary = None
    try:
        _validate_parent_fd(parent_fd)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise GateFailure("not_regular:" + path.as_posix())
        expected_identity = _identity(expected) if isinstance(expected, os.stat_result) else expected
        if expected_identity is not None and _identity(before) != expected_identity:
            raise GateFailure("file_identity_drift:" + path.as_posix())
        data = os.read(fd, limit)
        after = os.fstat(fd)
        current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        _validate_parent_fd(parent_fd)
        if jumbo_pair._fingerprint(before) != jumbo_pair._fingerprint(after) or jumbo_pair._fingerprint(after) != jumbo_pair._fingerprint(current):
            raise GateFailure("file_identity_drift:" + path.as_posix())
        return data
    except BaseException as exc:
        primary = exc
        raise
    finally:
        _finish_reader(parent_fd, fd, primary)


def git_head() -> str:
    head = read_bytes_nofollow(ROOT / ".git/HEAD").decode("ascii").strip()
    if head.startswith("ref: "):
        ref = ROOT / ".git" / head[5:]
        if ref.exists():
            head = read_bytes_nofollow(ref).decode("ascii").strip()
        else:
            for line in read_bytes_nofollow(ROOT / ".git/packed-refs").decode("ascii").splitlines():
                if line and not line.startswith(("#", "^")):
                    digest, name = line.split(" ", 1)
                    if name == head[5:]:
                        head = digest
                        break
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise GateFailure("git_head")
    return head


def parse_json_bytes(raw: bytes, path: Path) -> Any:
    def no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise GateFailure("duplicate_json_key")
            out[key] = value
        return out

    try:
        payload = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise GateFailure("json_non_utf8:" + path.as_posix()) from exc
    def nonfinite(_value: str) -> None:
        raise GateFailure("json_nonfinite:" + path.as_posix())
    return json.loads(payload, object_pairs_hook=no_dupes, parse_constant=nonfinite)


def load_json(path: Path) -> Any:
    return parse_json_bytes(read_bytes_nofollow(path), path)


def load_config() -> dict[str, Any]:
    cfg = load_json(CONFIG_PATH)
    expected_top = {
        "schema_version", "protocol_id", "source", "authority", "runtime", "state_order", "control_plane",
        "license", "pedigree", "role", "support", "overlap", "payload", "gates",
        "containment", "decision_rules", "history", "capability", "authorizations", "acquisition_limits",
    }
    if set(cfg) != expected_top:
        raise GateFailure("config_top_level_keys")
    if cfg.get("schema_version") != "msae_independent_norspan_v1_protocol_v1":
        raise GateFailure("config_schema")
    if cfg.get("protocol_id") != "NORSPAN-1":
        raise GateFailure("config_protocol_id")
    if set(cfg["authority"]) != {"plan_path", "plan_sha256", "plan_review_path",
                                  "plan_review_sha256", "todo_sha256", "v10_reference_sha256"}:
        raise GateFailure("config_authority_keys")
    if cfg["source"] != {
        "repo": REPO,
        "commit": COMMIT,
        "files": [*SOURCE_FILES.values(), LICENSE_FILE],
    }:
        raise GateFailure("config_source")
    if canonical_bytes(cfg["acquisition_limits"]) != canonical_bytes({
        "command_timeout_seconds": 600, "stdout_limit_bytes": 16777216, "stderr_limit_bytes": 4194304,
    }):
        raise GateFailure("config_acquisition_limits")
    if set(cfg["runtime"]) != {"python", "unicode"}:
        raise GateFailure("config_runtime_keys")
    if tuple(sys.version_info[:3]) != tuple(cfg["runtime"]["python"]):
        raise GateFailure("python_version")
    if unicodedata.unidata_version != cfg["runtime"]["unicode"]:
        raise GateFailure("unicode_version")
    expected_state_order = [
        "clean_reviewed", "baseline", "authority", "acquisition_entered", "network_ready",
        "network_started", "acquisition_terminal", "scientific_entered", "raw_ready",
        "raw_started", "scientific_terminal",
    ]
    if cfg["state_order"] != expected_state_order:
        raise GateFailure("config_state_order")
    if cfg["control_plane"] != {
        "review_ship_first_line": "VERDICT: SHIP",
        "authority_control_modes": {key: value for key, value in LEGACY_AUTHORITY_CONTROL_MODES.items()},
        "scientific_prefix": list(SCIENCE_PREFIX),
        "unresolved_no_retry_states": ["network_started_without_terminal",
                                        "raw_started_without_terminal", "partial_raw",
                                        "partial_private", "temporary_object"],
        "raw_mode": 0o444, "private_file_mode": 0o600,
        "private_directory_mode": 0o700, "raw_file_count": 4,
        "private_role_count": 4,
    }:
        raise GateFailure("config_control_plane")
    expected_license = {
        "max_bytes": 131072,
        "accepted_phrases": [list(x) for x in (
            ("cc", "by", "sa", "4", "0"),
            ("creative", "commons", "attribution", "sharealike", "4", "0"),
            ("attribution", "sharealike", "4", "0", "international"),
        )],
        "accepted_urls": [
            "http://creativecommons.org/licenses/by-sa/4.0",
            "http://creativecommons.org/licenses/by-sa/4.0/",
            "https://creativecommons.org/licenses/by-sa/4.0",
            "https://creativecommons.org/licenses/by-sa/4.0/",
        ],
        "negative_phrases": [list(x) for x in (
            ("all", "rights", "reserved"), ("no", "redistribution"),
            ("non", "commercial", "use", "only"),
        )],
        "contradictory_identifiers": [
            "agpl-3.0", "cc-by-nc-4.0", "cc-by-nd-4.0", "gpl-2.0", "gpl-3.0", "proprietary",
        ],
    }
    if cfg["license"] != expected_license:
        raise GateFailure("config_license")
    if cfg["role"] != {
        "domain": "norspan-1/role-v1",
        "cutpoints_u64": [11068046444225730969, 14757395258967641292, 16602069666338596454],
        "names": ["discovery", "calibration", "C1", "C2"],
    }:
        raise GateFailure("config_role")
    if (set(cfg["support"]["required_tasks"]) != REQUIRED
            or set(cfg["support"]["optional_tasks"]) != OPTIONAL
            or cfg["support"]["distinct_sentence_floor"] != 20
            or cfg["support"]["minimum_optional_tasks"] != 2
            or set(cfg["support"]["upos"]) != UPOS
            or set(cfg["support"]["deprel"]) != DEPREL
            or set(cfg["support"]["number"]) != NUMBER
            or bytes.fromhex(cfg["support"]["token_domain_hex"]) != b"norspan-1/token\0"
            or bytes.fromhex(cfg["support"]["lemma_domain_hex"]) != b"norspan-1/lemma\0"):
        raise GateFailure("config_support")
    if tuple(tuple(x) for x in cfg["pedigree"]["identifiers"]) != ALIAS_SEQUENCES:
        raise GateFailure("config_pedigree_identifiers")
    if bytes.fromhex(cfg["pedigree"]["domain_hex"]) != b"norspan-1/pedigree\0":
        raise GateFailure("config_pedigree_domain")
    if cfg["overlap"] != {
        "short_max_tokens": 9, "long_min_tokens": 10, "fivegram_jaccard_min": 0.8,
        "covered_fivegrams_min": 4, "covered_tokens_min": 20, "covered_fraction_min": 0.1,
    }:
        raise GateFailure("config_overlap")
    if cfg["payload"] != {
        "schema_version": "msae_independent_norspan_v1_payload_v1",
        "roles": ["discovery", "calibration", "C1", "C2"],
        "file_mode": 384, "directory_mode": 448,
    }:
        raise GateFailure("config_payload")
    if cfg["authorizations"] != {
        "model_scoring": False, "gpu_query": False,
        "k2_or_branch_training": False, "stage_c": False,
    }:
        raise GateFailure("config_authorizations")
    gates = cfg["gates"]
    if set(gates) != {"finite_draws_required", "finite_draws_total", "broad_recovery_min",
                     "broad_leakage_max", "selectivity_margin_min", "family_advantage_margin",
                     "retention_margin", "collateral_margin", "stability_margin", "outputs",
                     "case_precedence"}:
        raise GateFailure("config_gate_keys")
    if (gates["finite_draws_required"], gates["finite_draws_total"], gates["broad_recovery_min"],
        gates["broad_leakage_max"], gates["selectivity_margin_min"], gates["family_advantage_margin"],
        gates["retention_margin"], gates["collateral_margin"], gates["stability_margin"],
        gates["outputs"], gates["case_precedence"]) != (
        450, 500, 0.75, 0.55, 0.2, 0.05, 0.02, 0.02, 0.05,
        ["learned_model", "existing_or_simple", "negative_atlas", "equivocal_no_decision"],
        ["ioi", "controlled_relation_position"],
    ):
        raise GateFailure("config_gates")
    if cfg["history"] != {"archive_max_members": 10000,
                          "archive_max_member_bytes": 67108864,
                          "archive_max_total_bytes": 536870912,
                          "protected_content_reads": 0}:
        raise GateFailure("config_history")
    if cfg["containment"] != {
        "prescore_roles": ["discovery", "calibration", "C1"],
        "prescore_forbidden_roles": ["C2"],
        "c1_requires": ["readiness_ship", "immutable_scoring_manifest", "prescore_ship",
                        "c1_capability"],
        "c2_requires": ["signed_g3", "m5_frozen", "m6_passed", "branch_prerequisites",
                        "m8_capability"],
        "network": False, "host_ipc": False, "host_sockets": False,
        "regular_file_limit_bytes": 8589934592, "open_file_limit": 4096,
        "process_limit": 512, "run_total_bytes_limit": 68719476736,
        "run_entry_limit": 65536,
    }:
        raise GateFailure("config_containment")
    if cfg["decision_rules"] != {
        "precedence": ["learned_model", "existing_or_simple", "negative_atlas",
                       "equivocal_no_decision"],
        "equivocal_conditions": ["conflicting_metrics", "boundary_interval_overlap",
                                  "insufficient_finite_draws", "failed_stability",
                                  "failed_specificity", "inadequate_power"],
        "negative_requires": ["c1_technically_valid", "all_endpoints_finite",
                              "stable_null_direction", "no_family_passes_g1",
                              "all_upper_bounds_exclude_material_margin"],
        "equivocal_authorizes_c2": False, "equivocal_authorizes_training": False,
        "one_signed_g3_branch": True, "one_pre_c2_case": True,
    }:
        raise GateFailure("config_decision_rules")
    if cfg["capability"] != {
        "process_tokens": ["nvidia-smi", "torchrun", "accelerate", "deepspeed", "train",
                           "training", "score", "scoring", "evaluate", "evaluation",
                           "inference", "vllm", "tmux"],
        "environment_keys": ["CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES", "LOCAL_RANK",
                             "RANK", "WORLD_SIZE", "TMUX"],
        "training_roots": ["results", "pilot_runs", "checkpoints", "runs"],
        "content_hash_max_bytes": 67108864,
    }:
        raise GateFailure("config_capability")
    bound = {
        ROOT / cfg["authority"]["plan_path"]: cfg["authority"]["plan_sha256"],
        ROOT / cfg["authority"]["plan_review_path"]: cfg["authority"]["plan_review_sha256"],
        ROOT / "TODO.md": cfg["authority"]["todo_sha256"],
        ROOT / "scripts/prepare_msae_independent_source_v10.py": cfg["authority"]["v10_reference_sha256"],
    }
    for path, expected in bound.items():
        if sha_file(path) != expected:
            raise GateFailure("authority_hash_drift:" + path.relative_to(ROOT).as_posix())
    if not review_is_ship(ROOT / cfg["authority"]["plan_review_path"]):
        raise GateFailure("plan_review_not_ship")
    return cfg


def publish_bytes(path: Path, payload: bytes, mode: int = 0o644) -> jumbo_pair.PairReceipt:
    """Create a permanent pair, returning its owned-producer receipt.

    The receipt alone never grants containing authority. Ordinary readers and
    canonical trust/schema integration must be completed before production use.
    """
    _relative_to_root(path)
    ensure_directory(path.parent, 0o755)
    receipt = jumbo_pair.create_pair(path, payload, mode=mode)
    session = _PAIR_SESSION.get()
    if session is not None and _paired_control_name(path) is not None:
        session.register(path.name, receipt)
    return receipt


def publish_json(path: Path, value: Any, mode: int = 0o644) -> jumbo_pair.PairReceipt:
    return publish_bytes(path, canonical_file_bytes(value), mode)


def _dir_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    fd = _open_parent_fd(path / "sentinel")
    primary = None
    try:
        names = jpc_runtime.bounded_names(fd,jpc_runtime.ENTRY_LIMIT)
        _validate_parent_fd(fd)
        return names
    except BaseException as exc:
        primary = exc
        raise
    finally:
        _close_parent_fd(fd, primary=primary)


def _descriptor_tree(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    parent = None
    root_fd = None
    primary = None
    records = []
    def walk(fd, parts):
        if len(parts) > 64:
            raise GateFailure("protocol_tree_depth_budget")
        for name in sorted(jpc_runtime.bounded_names(fd,jpc_runtime.ENTRY_LIMIT-len(records))):
            if name == '.msae_keys':
                raise GateFailure('history_credential_namespace_prohibited')
            if len(records) >= jpc_runtime.ENTRY_LIMIT:
                raise GateFailure("protocol_tree_object_budget")
            child = os.stat(name, dir_fd=fd, follow_symlinks=False)
            rel_parts = (*parts, name)
            rel = PurePosixPath(*rel_parts).as_posix()
            kind = ("directory" if stat.S_ISDIR(child.st_mode) else
                    "regular" if stat.S_ISREG(child.st_mode) else
                    "symlink" if stat.S_ISLNK(child.st_mode) else "special")
            records.append({"path": rel, "kind": kind, "mode": stat.S_IMODE(child.st_mode),
                            "nlink": child.st_nlink, "size": child.st_size,
                            "device": child.st_dev, "inode": child.st_ino,
                            "mtime_ns": child.st_mtime_ns})
            if kind == "directory":
                if len(rel_parts) > 64:
                    raise GateFailure("protocol_tree_depth_budget")
                child_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                error = None
                try:
                    if _identity(os.fstat(child_fd))[:4] != _identity(child)[:4]:
                        raise GateFailure("protocol_ancestor_drift:" + rel)
                    walk(child_fd, rel_parts)
                    if _identity(os.stat(name, dir_fd=fd, follow_symlinks=False))[:4] != _identity(child)[:4]:
                        raise GateFailure("protocol_ancestor_drift:" + rel)
                except BaseException as exc:
                    error = exc
                    raise
                finally:
                    jumbo_pair._close_fds([child_fd], primary=error)
    try:
        try:
            parent = _open_parent_fd(path)
            st = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            if parent is not None:
                _validate_parent_fd(parent)
            return None, []
        if not stat.S_ISDIR(st.st_mode):
            raise GateFailure("protocol_root_not_directory:" + path.as_posix())
        root_fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        if _identity(os.fstat(root_fd))[:4] != _identity(st)[:4]:
            raise GateFailure("protocol_root_identity_drift")
        root_record = {"type": stat.S_IFMT(st.st_mode), "mode": stat.S_IMODE(st.st_mode),
                       "nlink": st.st_nlink, "device": st.st_dev, "inode": st.st_ino}
        walk(root_fd, ())
        _validate_parent_fd(parent)
        if _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False))[:4] != _identity(st)[:4]:
            raise GateFailure("protocol_root_identity_drift")
        return root_record, records
    except BaseException as exc:
        primary = exc
        raise
    finally:
        if parent is not None:
            _finish_reader(parent, root_fd, primary)


def protocol_inventory() -> dict[str, Any]:
    prov_root, prov_entries = _descriptor_tree(PROV)
    public = {row["path"] for row in prov_entries if row["kind"] == "regular" and "/" not in row["path"]}
    public_invalid = [row["path"] for row in prov_entries
                      if row["kind"] != "regular" or "/" in row["path"]]
    if prov_root is not None:
        paired = _expected_session().inventory()
        if paired["partial"]:
            raise GateFailure("partial_public_evidence_unresolved")
        public = set(paired["logical"])
        public_invalid = []
    unknown_public = public - PHASE_PUBLIC
    data_root, data_entries = _descriptor_tree(DATA)
    data_dirs = {row["path"] for row in data_entries if row["kind"] == "directory"}
    data_files = {row["path"] for row in data_entries if row["kind"] == "regular"}
    data_other = {row["path"] for row in data_entries if row["kind"] not in {"directory", "regular"}}
    if data_root is not None and data_files:
        session = _expected_session()
        controls = set(session.catalog()["controls"])
        raw_manifest = session.raw_manifest
        private_manifest = session.private_manifest
        if "source_acquisition.json" in controls:
            raw_manifest = session.canonical("source_acquisition.json")["files"]
        if "seal.json" in controls:
            private_manifest = session.canonical("seal.json")["payloads"]
        elif "source_ready.json" in controls:
            private_manifest = session.canonical("source_ready.json")["payloads"]
        expected_pairs = {}
        if raw_manifest is not None:
            if type(raw_manifest) is not dict or set(raw_manifest) != {*SOURCE_FILES.values(),LICENSE_FILE}:
                raise GateFailure("raw_inventory_outside_manifest_schema")
            for name,item in raw_manifest.items():
                expected_pairs[f"raw/{COMMIT}/{name}"] = (RAW/name,item,0o444)
        if private_manifest is not None:
            if type(private_manifest) is not dict or set(private_manifest) != set(jpc_runtime.ROLES):
                raise GateFailure("private_inventory_outside_manifest_schema")
            for role,item in private_manifest.items():
                path = PRIVATE/role.lower()/"payload.jsonl"
                expected_pairs[f"private/{role.lower()}/payload.jsonl"] = (path,item,0o600)
        rows = {row["path"]:row for row in data_entries}
        stage_names = set()
        for rel,(path,item,mode) in expected_pairs.items():
            manifest = {key:item[key] for key in ["sha256","bytes","mode","nlink","pair"]}
            receipt = jpc_runtime._expected_receipt(path,manifest,mode)
            stage = str(PurePosixPath(rel).with_name("."+path.name+".stage"))
            for alias in [rel,stage]:
                row = rows.get(alias)
                if row is None or row["kind"] != "regular" or (row["device"],row["inode"],row["mode"],row["size"],row["nlink"]) != (receipt.device,receipt.inode,receipt.mode,receipt.byte_count,2):
                    raise GateFailure("data_inventory_expected_pair_drift:"+alias)
            stage_names.add(stage)
        physical = set(expected_pairs) | stage_names
        if data_files != physical:
            raise GateFailure("data_inventory_partial_or_foreign")
        data_files -= stage_names
    raw_files = {rel for rel in data_files if rel.startswith("raw/")}
    private_files = {rel for rel in data_files if rel.startswith("private/")}
    return {
        "public_root": prov_root, "data_root": data_root,
        "public_manifest": prov_entries,
        "public": sorted(public), "unknown_public": sorted(unknown_public | set(public_invalid)),
        "data_dirs": sorted(data_dirs), "data_files": sorted(data_files),
        "data_other": sorted(data_other),
        "data_manifest": data_entries,
        "raw_files": sorted(raw_files), "private_files": sorted(private_files),
    }


def classify_protocol_state() -> str:
    inv = protocol_inventory()
    public = set(inv["public"])
    if inv["unknown_public"]:
        raise GateFailure("protocol_extra_public:" + ",".join(inv["unknown_public"]))
    if inv["public_root"] is not None and inv["public_root"]["mode"] != 0o755:
        raise GateFailure("protocol_public_root_mode")
    if any(row["mode"] != 0o644 or row["nlink"] != 2 for row in inv["public_manifest"]):
        raise GateFailure("protocol_public_file_custody")
    if inv["data_other"]:
        raise GateFailure("protocol_special_data:" + ",".join(inv["data_other"]))
    raw_expected = {f"raw/{COMMIT}/{name}" for name in [*SOURCE_FILES.values(), LICENSE_FILE]}
    raw_dirs = {"raw", f"raw/{COMMIT}"}
    private_expected = {f"private/{role}/payload.jsonl" for role in ("discovery", "calibration", "c1", "c2")}
    private_dirs = {"private", "private/discovery", "private/calibration", "private/c1", "private/c2"}
    all_files = set(inv["data_files"])
    all_dirs = set(inv["data_dirs"])
    if all_files - raw_expected - private_expected or all_dirs - raw_dirs - private_dirs:
        raise GateFailure("protocol_extra_data")
    modes = {row["path"]: row["mode"] for row in inv["data_manifest"]}
    data_records = {row["path"]: row for row in inv["data_manifest"]}
    raw_shape = (set(inv["raw_files"]) == raw_expected and raw_dirs <= all_dirs
                 and inv["data_root"] is not None and inv["data_root"]["mode"] == 0o700
                 and modes.get("raw") == 0o700 and modes.get(f"raw/{COMMIT}") == 0o555
                 and all(data_records[name]["mode"] == 0o444 and data_records[name]["nlink"] == 2
                         for name in raw_expected))
    private_shape = (set(inv["private_files"]) == private_expected and private_dirs <= all_dirs
                     and all(modes.get(name) == 0o700 for name in private_dirs)
                     and all(data_records[name]["mode"] == 0o600 and data_records[name]["nlink"] == 2
                             for name in private_expected))
    no_data = inv["data_root"] is None
    base = {"current_history_registry.json", "baseline.json"}
    if not public and no_data:
        return "clean_reviewed"
    if public == base and no_data:
        return "baseline"
    authority = base | {"authority.json"}
    review = ROOT / "reports/adversarial/msae_independent_norspan_v1_authority_review.md"
    if public == authority and review.exists() and no_data:
        return "authority"
    entered = authority | {"acquisition_entry.json"}
    if public == entered and no_data:
        return "acquisition_entered"
    network_ready = entered | {"pre_network_ready.json"}
    if public == network_ready and no_data:
        return "network_ready"
    network_started = network_ready | {"network_started.json"}
    if public == network_started and no_data:
        return "network_started"
    if "rejection.json" in public:
        expected = network_started | {"rejection.json"}
        science_started = network_started | {"source_acquisition.json", "scientific_entry.json",
                                             "pre_raw_ready.json", "raw_access_started.json"}
        if public == expected and no_data:
            return "acquisition_terminal"
        if public.issuperset(science_started | {"rejection.json"}) and not {
                "source_ready.json", "no_training_gate.json", "seal.json"} & public:
            prefix = [name for name in SCIENCE_PREFIX if name in public]
            if set(prefix) == (public - science_started - {"rejection.json"}) \
                    and prefix == list(SCIENCE_PREFIX[:len(prefix)]) and raw_shape \
                    and not inv["private_files"] and all_dirs == raw_dirs:
                return "scientific_terminal"
        raise GateFailure("invalid_rejection_state")
    acquisition_success = network_started | {"source_acquisition.json"}
    if public == acquisition_success and raw_shape and all_dirs == raw_dirs and not inv["private_files"]:
        return "acquisition_terminal"
    sci_entered = acquisition_success | {"scientific_entry.json"}
    if public == sci_entered and raw_shape and all_dirs == raw_dirs and not inv["private_files"]:
        return "scientific_entered"
    raw_ready = sci_entered | {"pre_raw_ready.json"}
    if public == raw_ready and raw_shape and all_dirs == raw_dirs and not inv["private_files"]:
        return "raw_ready"
    raw_started = raw_ready | {"raw_access_started.json"}
    if public == raw_started and raw_shape and all_dirs == raw_dirs and not inv["private_files"]:
        return "raw_started"
    terminal = raw_started | set(SCIENCE_PREFIX) | {"source_ready.json", "no_training_gate.json", "seal.json"}
    if public == terminal and raw_shape and private_shape and all_dirs == raw_dirs | private_dirs:
        return "scientific_terminal"
    raise GateFailure("unrecognized_protocol_state")


def _git_porcelain_snapshot() -> dict[str, Any]:
    import acquire_msae_independent_norspan_v1 as acquisition
    stdout, _stderr, code = acquisition.run(
        ["git", "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null",
         "-c", "core.fsmonitor=false", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=ROOT,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1"},
        timeout_seconds=30, stdout_limit_bytes=4*1024**2, stderr_limit_bytes=1024**2)
    if code:
        raise GateFailure("git_porcelain_failed")
    entries = []
    for raw in stdout.split(b"\0"):
        if not raw:
            continue
        text = raw.decode("utf-8", "surrogateescape")
        path = text[3:] if len(text) >= 3 else text
        if (path.startswith("reports/provenance/msae_independent_norspan_v1/")
                or path.startswith("data/msae_independent_norspan_v1/")
                or path in ALLOWED_AUTHORITY_PATHS):
            continue
        entries.append(text)
    entries.sort()
    return {"outside_protocol_count": len(entries),
            "outside_protocol_sha256": sha_bytes(canonical_bytes(entries))}


def _training_snapshot() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for relroot in ("results", "pilot_runs", "checkpoints", "runs"):
        root = ROOT / relroot
        root_record, tree = _descriptor_tree(root)
        if root_record is None:
            continue
        entries.append({"path": relroot, "kind": "root", **root_record, "sha256": None})
        for row in tree:
            item = {**row, "path": relroot + "/" + row["path"], "sha256": None}
            if row["kind"] == "regular" and row["size"] <= 67108864 \
                    and Path(row["path"]).suffix.lower() not in MODEL_SUFFIXES:
                expected = (row["device"], row["inode"], stat.S_IFREG, row["mode"],
                            row["nlink"], row["size"])
                item["sha256"] = sha_file(root / row["path"], expected)
            entries.append(item)
    entries.sort(key=lambda item: item["path"])
    return {"entry_count": len(entries), "manifest_sha256": sha_bytes(canonical_bytes(entries))}


def process_capability_reasons(cmd: bytes, cwd: str, environ: bytes) -> tuple[list[str], list[str]]:
    project = str(ROOT).encode() in cmd or cwd.startswith(str(ROOT))
    if not project:
        return [], []
    low = cmd.lower()
    token_hits = [token for token in CAPABILITY_PROCESS_TOKENS if token.encode() in low]
    env_names = {field.split(b"=", 1)[0].decode("ascii", "ignore")
                 for field in environ.split(b"\0") if b"=" in field}
    env_hits = sorted(set(CAPABILITY_ENV_KEYS) & env_names)
    return token_hits, env_hits


def _process_snapshot() -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    scanned = 0
    for item in sorted(Path("/proc").iterdir(), key=lambda p: p.name):
        if not item.name.isdigit():
            continue
        try:
            cmd = (item / "cmdline").read_bytes().replace(b"\0", b" ")[:16384]
            cwd = os.readlink(item / "cwd")
            environ = (item / "environ").read_bytes()[:1048576]
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
        scanned += 1
        token_hits, env_hits = process_capability_reasons(cmd, cwd, environ)
        if token_hits or env_hits:
            matches.append({"pid": int(item.name), "cmdline_sha256": sha_bytes(cmd),
                            "cwd_sha256": sha_bytes(cwd.encode()),
                            "process_token_hits": token_hits, "environment_key_hits": env_hits,
                            "environment_sha256": sha_bytes(environ)})
    return {"scanned_process_count": scanned, "prohibited_match_count": len(matches),
            "matches": matches}


_RECOVERY_COUNTS = contextvars.ContextVar("norspan_recovery_counts", default=None)


def evidence_snapshot() -> dict[str, Any]:
    process = _process_snapshot()
    if process["prohibited_match_count"]:
        raise GateFailure("prohibited_process_active")
    counts = _RECOVERY_COUNTS.get()
    if counts is not None:
        counts['local_status_observation_attempts'] += 1
    porcelain = _git_porcelain_snapshot()
    if counts is not None:
        counts['local_status_observation_completed'] += 1
    return {"process": process, "training": _training_snapshot(),
            "porcelain": porcelain, "model_operations": 0,
            "gpu_queries": 0, "training_runs": 0}


def evidence_compatible(baseline: dict[str, Any], current: dict[str, Any]) -> None:
    if baseline["training"] != current["training"]:
        raise GateFailure("training_state_drift")
    if baseline["porcelain"] != current["porcelain"]:
        raise GateFailure("porcelain_state_drift")
    if current["process"]["prohibited_match_count"]:
        raise GateFailure("prohibited_process_active")


def lexical_tokens(text: str) -> tuple[str, ...]:
    return tuple(x.casefold() for x in LEX.findall(unicodedata.normalize("NFKC", text)))


def fivegrams(tokens: tuple[str, ...]) -> set[tuple[str, ...]]:
    return {tokens[i:i + 5] for i in range(max(0, len(tokens) - 4))}


def overlap_reason(candidate: tuple[str, ...], other: tuple[str, ...]) -> str | None:
    if not candidate or not other:
        return None
    if candidate == other:
        return "exact"
    if len(candidate) <= 9 and len(other) > len(candidate):
        if any(other[i:i + len(candidate)] == candidate for i in range(len(other) - len(candidate) + 1)):
            return "contained_short"
    if len(candidate) >= 10 and len(other) >= 10:
        a, b = fivegrams(candidate), fivegrams(other)
        shared = a & b
        if shared and len(shared) / len(a | b) >= 0.8:
            return "fivegram_jaccard"
        covered: set[int] = set()
        for i in range(len(candidate) - 4):
            if candidate[i:i + 5] in b:
                covered.update(range(i, i + 5))
        if len(shared) >= 4 and len(covered) >= 20 and len(covered) / len(candidate) >= 0.1:
            return "covered_fivegrams"
    return None


def _unsafe_history_path(rel: str) -> bool:
    parts = PurePosixPath(rel).parts
    if rel in QUARANTINES or "private" in parts:
        return True
    return any(rel == p[:-1] or rel.startswith(p) for p in EXCLUDED_PREFIXES)


def _history_objects() -> Iterator[tuple[str, Path, os.stat_result, str]]:
    """Retain admitted originals through the full finite public-history census.

    Admission failure BLOCKS full history, never samples it. Protected/model
    bytes are not read. This is controlled-writer observation, NOT atomicity.
    """
    root_fd = _open_parent_fd(ROOT / "sentinel")
    owned, directories, aliases, files = [], [], [], []
    admitted = total_bytes = 0
    primary = None

    def retain(parent, name, before, *, directory, path):
        _reader_fd_admission(path)
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        if directory: flags |= os.O_DIRECTORY
        child = os.open(name,flags,dir_fd=parent)
        owned.append(child)  # BEFORE any fstat that can fail.
        if jumbo_pair._fingerprint(os.fstat(child)) != jumbo_pair._fingerprint(before):
            raise GateFailure("history_original_identity_drift:"+name)
        return child

    def digest(fd, count):
        h=hashlib.sha256();offset=0
        while block:=os.pread(fd,min(1024**2,count-offset+1),offset):
            offset+=len(block)
            if offset>count:raise GateFailure("history_original_growth")
            h.update(block)
        if offset!=count:raise GateFailure("history_original_short_read")
        return h.hexdigest()

    def walk(fd, parts):
        nonlocal admitted,total_bytes
        if len(parts)>64:raise GateFailure("history_depth_budget")
        before_dir=jumbo_pair._fingerprint(os.fstat(fd))
        names=jpc_runtime.bounded_names(fd,jpc_runtime.ENTRY_LIMIT-admitted,reason="history_object_budget")
        directories.append((fd,before_dir,names))
        for name in sorted(names):
            if name == '.msae_keys':
                raise GateFailure('history_credential_namespace_prohibited')
            if admitted>=jpc_runtime.ENTRY_LIMIT:raise GateFailure("history_object_budget")
            admitted+=1
            if name in {".",".."} or "/" in name or "\0" in name:raise GateFailure("history_bad_name")
            rel_parts=(*parts,name);rel=PurePosixPath(*rel_parts).as_posix();path=ROOT.joinpath(*rel_parts)
            before=os.stat(name,dir_fd=fd,follow_symlinks=False)
            aliases.append((fd,name,jumbo_pair._fingerprint(before)))
            if stat.S_ISLNK(before.st_mode):
                yield rel,path,before,"symlink_lstat_only";continue
            if stat.S_ISDIR(before.st_mode):
                if _unsafe_history_path(rel+"/"):
                    yield rel,path,before,"protected_directory_lstat_only"
                    exact=sorted(PurePosixPath(item).name for item in QUARANTINES if PurePosixPath(item).parent.as_posix()==rel)
                    if exact:
                        child=retain(fd,name,before,directory=True,path=path)
                        for child_name in exact:
                            try:child_st=os.stat(child_name,dir_fd=child,follow_symlinks=False)
                            except FileNotFoundError:continue
                            if admitted>=jpc_runtime.ENTRY_LIMIT:raise GateFailure("history_object_budget")
                            admitted+=1
                            aliases.append((child,child_name,jumbo_pair._fingerprint(child_st)))
                            child_rel=(PurePosixPath(rel)/child_name).as_posix()
                            yield child_rel,ROOT/child_rel,child_st,"quarantine_file_lstat_only"
                    continue
                if len(rel_parts)>64:raise GateFailure("history_depth_budget")
                child=retain(fd,name,before,directory=True,path=path)
                yield rel,path,before,"public_directory_lstat_only"
                yield from walk(child,rel_parts)
                continue
            if not stat.S_ISREG(before.st_mode):
                yield rel,path,before,"special_lstat_only";continue
            if _unsafe_history_path(rel):
                yield rel,path,before,"protected_file_lstat_only";continue
            if path.suffix.lower() not in MODEL_SUFFIXES:
                if before.st_size>jpc_runtime.FILE_BYTES_LIMIT or total_bytes+before.st_size>jpc_runtime.TOTAL_BYTES_LIMIT:
                    raise GateFailure("history_observed_byte_admission")
                total_bytes+=before.st_size
                logical=None
                if path.parent==PROV:
                    logical=next((item for item in PHASE_PUBLIC if name in {item,"."+item+".stage"}),None)
                if logical is not None:
                    expected=_expected_session().expected(logical)
                    jumbo_pair._check_stat(before,expected,2)
                    expected_digest=expected.sha256
                elif before.st_nlink!=1:
                    raise GateFailure("history_ordinary_nlink:"+rel)
                child=retain(fd,name,before,directory=False,path=path)
                observed=digest(child,before.st_size)
                if logical is not None and observed!=expected_digest:
                    raise GateFailure("history_paired_expected_bytes:"+rel)
                files.append((child,before.st_size,observed,jumbo_pair._fingerprint(before)))
            yield rel,path,before,"candidate_regular"

    try:
        yield from walk(root_fd,())
        for fd,count,expected,fp in files:
            if digest(fd,count)!=expected:raise GateFailure("history_final_expected_bytes")
        # ALL original FDs and named aliases after the last consumer/digest.
        for fd,count,expected,fp in files:
            if jumbo_pair._fingerprint(os.fstat(fd))!=fp:raise GateFailure("history_final_original_drift")
        for fd,fp,names in directories:
            if jpc_runtime.bounded_names(fd,len(names))!=names or jumbo_pair._fingerprint(os.fstat(fd))!=fp:
                raise GateFailure("history_final_directory_drift")
        for parent,name,fp in aliases:
            if jumbo_pair._fingerprint(os.stat(name,dir_fd=parent,follow_symlinks=False))!=fp:
                raise GateFailure("history_final_named_drift")
        _validate_parent_fd(root_fd)
    except BaseException as exc:
        primary=exc
        raise
    finally:
        first=primary
        try:jumbo_pair._close_fds(reversed(owned),primary=first)
        except BaseException as exc:first=exc
        _close_parent_fd(root_fd,primary=first)
        if primary is None and first is not None:raise first


@contextlib.contextmanager
def _history_census():
    """Close originals immediately, forwarding a consumer's primary failure.

    Throwing the primary into the suspended producer lets its all-release
    cleanup attach secondary faults to that primary, not lost GeneratorExit.
    """
    walker = _history_objects()
    primary = None
    try:
        yield walker
    except BaseException as exc:
        primary = exc
        raise
    finally:
        if primary is None:
            walker.close()
        else:
            try:
                walker.throw(primary)
            except BaseException as exc:
                if exc is not primary:
                    primary.add_note("history producer cleanup: " + repr(exc))


def _safe_member_name(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(name) and not name.startswith(("/", "\\")) and "\\" not in name and "\0" not in name and ".." not in p.parts


def _archive_text_members(path: Path, cfg: dict[str, Any],
                          expected: os.stat_result | tuple[int, int, int, int, int, int] | None = None) -> Iterator[tuple[str, str]]:
    limits = cfg["history"]
    max_members = limits["archive_max_members"]
    max_member = limits["archive_max_member_bytes"]
    max_total = limits["archive_max_total_bytes"]
    total = 0
    seen: set[str] = set()

    def register(name: str) -> None:
        if not _safe_member_name(name) or name in seen:
            raise GateFailure("unsafe_archive_member")
        seen.add(name)
        if len(seen) > max_members:
            raise GateFailure("archive_limit")

    def accept(name: str, data: bytes, *, registered: bool = False) -> tuple[str, str]:
        nonlocal total
        if not registered:
            register(name)
        if len(data) > max_member:
            raise GateFailure("archive_limit")
        total += len(data)
        if total > max_total:
            raise GateFailure("archive_limit")
        low = name.lower()
        if low.endswith((".zip", ".tar", ".tgz", ".tar.gz", ".gz")):
            raise GateFailure("nested_archive")
        try:
            return name, data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GateFailure("archive_non_utf8") from exc

    raw = read_bytes_nofollow(path, max_bytes=max_total, expected=expected)
    low = path.name.lower()
    if raw.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for info in archive.infolist():
                register(info.filename)
                if info.is_dir():
                    continue
                if info.flag_bits & 1:
                    raise GateFailure("encrypted_archive")
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) and not stat.S_ISREG(mode):
                    raise GateFailure("unsafe_archive_member_type")
                if info.file_size > max_member or total + info.file_size > max_total:
                    raise GateFailure("archive_limit")
                with archive.open(info, "r") as handle:
                    data = handle.read(max_member + 1)
                    if handle.read(1):
                        raise GateFailure("archive_limit")
                yield accept(info.filename, data, registered=True)
        return
    is_gzip = raw.startswith(b"\x1f\x8b")
    is_tar = len(raw) >= 265 and raw[257:262] == b"ustar"
    if is_tar or is_gzip:
        try:
            archive_cm = tarfile.open(fileobj=io.BytesIO(raw), mode="r:*")
        except tarfile.ReadError:
            archive_cm = None
        if archive_cm is not None:
            with archive_cm as archive:
                for member in archive:
                    register(member.name)
                    if member.isdir():
                        continue
                    if not member.isfile():
                        raise GateFailure("unsafe_archive_member_type")
                    if member.size > max_member or total + member.size > max_total:
                        raise GateFailure("archive_limit")
                    handle = archive.extractfile(member)
                    if handle is None:
                        raise GateFailure("archive_member_missing")
                    data = handle.read(max_member + 1)
                    if handle.read(1):
                        raise GateFailure("archive_limit")
                    yield accept(member.name, data, registered=True)
            return
        if not is_gzip:
            raise GateFailure("unsupported_archive_magic")
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as handle:
            data = handle.read(max_member + 1)
            if handle.read(1):
                raise GateFailure("archive_limit")
        yield accept(path.name[:-3] if low.endswith(".gz") else path.name + ".txt", data)
        return
    raise GateFailure("unsupported_archive_magic")


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for key in sorted(value):
            yield str(key)
            yield from _strings(value[key])


def text_units(text: str, suffix: str) -> Iterator[tuple[str, ...]]:
    if "\0" in text:
        raise GateFailure("history_nul")
    if suffix == ".json":
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            obj = None
        if obj is not None:
            for value in _strings(obj):
                tok = lexical_tokens(value)
                if tok:
                    yield tok
            return
    if suffix == ".jsonl":
        parsed = True
        rows: list[Any] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                parsed = False
                break
        if parsed:
            for row in rows:
                for value in _strings(row):
                    tok = lexical_tokens(value)
                    if tok:
                        yield tok
            return
    if suffix in {".csv", ".tsv"}:
        dialect = "excel-tab" if suffix == ".tsv" else "excel"
        for row in csv.reader(io.StringIO(text), dialect=dialect):
            for value in row:
                tok = lexical_tokens(value)
                if tok:
                    yield tok
        return
    for line in text.splitlines():
        tok = lexical_tokens(line)
        if tok:
            yield tok


def history_units(path: Path, adapter: str, cfg: dict[str, Any],
                  expected: os.stat_result | tuple[int, int, int, int, int, int] | None = None) -> Iterator[tuple[str, ...]]:
    if adapter == "archive":
        for name, text in _archive_text_members(path, cfg, expected):
            suffix = Path(name).suffix.lower()
            yield from text_units(text, suffix)
        return
    if adapter != "text":
        return
    data = read_bytes_nofollow(path, expected=expected)
    if b"\0" in data:
        raise GateFailure("history_text_nul:" + path.as_posix())
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateFailure("history_non_utf8:" + path.as_posix()) from exc
    yield from text_units(text, path.suffix.lower())


def classify_file(path: Path,
                  expected: os.stat_result | tuple[int, int, int, int, int, int] | None = None) -> str:
    low = path.name.lower()
    if path.suffix.lower() in MODEL_SUFFIXES:
        return "binary_excluded"
    prefix = read_prefix_nofollow(path, 65536, expected)
    archive_name = low.endswith((".zip", ".tar", ".tar.gz", ".tgz", ".gz"))
    archive_magic = (prefix.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08", b"\x1f\x8b"))
                     or (len(prefix) >= 265 and prefix[257:262] == b"ustar"))
    if archive_magic:
        return "archive"
    if archive_name:
        raise GateFailure("unsupported_archive_magic:" + path.as_posix())
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"LICENSE", "Makefile", ".gitignore", ".gitattributes"}:
        return "text"
    if b"\0" in prefix:
        raise GateFailure("unclassifiable_history_binary:" + path.as_posix())
    try:
        codecs.getincrementaldecoder("utf-8")("strict").decode(prefix, final=len(prefix) < 65536)
    except UnicodeDecodeError as exc:
        raise GateFailure("unclassifiable_history_binary:" + path.as_posix()) from exc
    return "text"


def alias_hits(tokens: tuple[str, ...]) -> list[str]:
    return [pedigree_hash(seq) for seq in ALIAS_SEQUENCES if tokens == seq]


def pedigree_hash(identifier: tuple[str, ...]) -> str:
    return sha_bytes(b"norspan-1/pedigree\0" + canonical_bytes(list(identifier)))


def build_history_registry(cfg: dict[str, Any]) -> dict[str, Any]:
    if DATA.exists() or PROV.exists():
        raise GateFailure("norspan_namespace_must_be_absent")
    entries: list[dict[str, Any]] = []
    alias_occurrences: list[dict[str, Any]] = []
    dispositions: collections.Counter[str] = collections.Counter()
    with _history_census() as census:
        for rel, path, st, disposition in census:
            adapter = disposition
            count = 0
            digest: str | None = None
            if disposition == "candidate_regular":
                adapter = classify_file(path, st)
            if adapter in {"text", "archive"}:
                for unit in history_units(path, adapter, cfg, st):
                    count += 1
                    hits = alias_hits(unit)
                    if hits:
                        alias_occurrences.append({"path": rel, "identifiers": sorted(set(hits))})
                digest = sha_file(path, st)
            try:
                final_st = path.lstat()
            except FileNotFoundError as exc:
                raise GateFailure("history_path_drift:" + rel) from exc
            if _identity(final_st) != _identity(st):
                raise GateFailure("history_path_drift:" + rel)
            path_hits = sorted({hit for component in PurePosixPath(rel).parts
                                for hit in alias_hits(lexical_tokens(component))})
            if path_hits:
                alias_occurrences.append({"path": rel, "identifiers": sorted(set(path_hits)), "kind": "path"})
            dispositions[adapter] += 1
            entries.append({
                "path": rel, "device": st.st_dev, "inode": st.st_ino,
                "type": stat.S_IFMT(st.st_mode), "mode": stat.S_IMODE(st.st_mode), "nlink": st.st_nlink,
                "size": st.st_size, "sha256": digest, "adapter": adapter,
                "extracted_unit_count": count,
            })
    entries.sort(key=lambda row: row["path"])
    blocked = sorted({item["path"] for item in alias_occurrences if item["path"] not in ALLOWED_AUTHORITY_PATHS})
    if blocked:
        raise GateFailure("prior_candidate_identity_use:" + ",".join(blocked[:10]))
    return {
        "schema_version": "msae_independent_norspan_v1_current_history_registry_v1",
        "temporal_scope": "all_policy_accessible_current_history_before_acquisition",
        "protected_v8_v10_content_gap": True,
        "protected_content_reads": 0,
        "entries": entries,
        "entry_count": len(entries),
        "disposition_counts": dict(sorted(dispositions.items())),
        "alias_occurrences": alias_occurrences,
        "candidate_identifier_hashes": [pedigree_hash(seq) for seq in ALIAS_SEQUENCES],
        "blocking_alias_occurrence_count": 0,
        "allowed_authority_paths": sorted(ALLOWED_AUTHORITY_PATHS),
        "status": "eligible",
    }


def require_jpc_qualification() -> None:
    try:
        jpc_runtime.require_whole_qualification()
    except jpc_runtime.RuntimeBlocked as exc:
        raise GateFailure(str(exc)) from exc


def cmd_build_history(args: argparse.Namespace) -> None:
    require_jpc_qualification()  # BEFORE any real state/evidence access.
    cfg = load_config()
    if classify_protocol_state() != "clean_reviewed":
        raise GateFailure("history_pre_state")
    review = canonical_implementation_review_path()
    if not review_is_ship(review):
        raise GateFailure("implementation_review_not_ship")
    # Prospective reviews and later phase objects cannot predate their authority.
    for rel in sorted(ALLOWED_AUTHORITY_PATHS - set(AUTHORITY_CONTROL_MODES)):
        try:
            (ROOT / rel).lstat()
        except FileNotFoundError:
            continue
        raise GateFailure("premature_protocol_control:" + rel)
    registry = build_history_registry(cfg)
    create_directory_exclusive(PROV, 0o755)
    publish_json(PROV / "current_history_registry.json", registry)
    baseline = {
        "schema_version": "msae_independent_norspan_v1_baseline_v1",
        "current_history_registry_sha256": sha_file(PROV / "current_history_registry.json"),
        "config_sha256": sha_file(CONFIG_PATH),
        "implementation_review_sha256": sha_file(review),
        "git_head": git_head(),
        "evidence": evidence_snapshot(),
        "source_namespace_absent_at_registry_start": True,
        "model_operations": 0, "gpu_queries": 0, "training_runs": 0,
        "status": "eligible",
    }
    publish_json(PROV / "baseline.json", baseline)
    if classify_protocol_state() != "baseline":
        raise GateFailure("baseline_post_state")


def cmd_build_authority(args: argparse.Namespace) -> None:
    require_jpc_qualification()  # BEFORE any real state/evidence access.
    cfg = load_config()
    if classify_protocol_state() != "baseline":
        raise GateFailure("authority_state")
    baseline = control_record("baseline.json")
    validate_evidence(baseline["evidence"])
    if baseline.get("current_history_registry_sha256") != sha_file(PROV / "current_history_registry.json"):
        raise GateFailure("baseline_registry_drift")
    current_evidence = evidence_snapshot()
    validate_evidence(current_evidence)
    evidence_compatible(baseline["evidence"], current_evidence)
    history_census = validate_history_registry(load_json(PROV / "current_history_registry.json"), cfg)
    controls = {rel:control_manifest(rel,mode) for rel,mode in sorted(AUTHORITY_CONTROL_MODES.items())}
    authority = {
        "schema_version": "msae_independent_norspan_v1_authority_v1",
        "source_repo": REPO, "source_commit": COMMIT,
        "source_files": [*SOURCE_FILES.values(), LICENSE_FILE],
        "baseline_sha256": sha_file(PROV / "baseline.json"),
        "current_history_registry_sha256": sha_file(PROV / "current_history_registry.json"),
        "controls": controls,
        "pre_authority_evidence": current_evidence,
        "pre_authority_history_census": history_census,
        "absent_at_publication": sorted(
            rel for rel in ALLOWED_AUTHORITY_PATHS if not (ROOT / rel).exists()
        ),
        "model_operations": 0, "gpu_queries": 0, "training_runs": 0,
        "status": "awaiting_independent_authority_review",
    }
    publish_json(PROV / "authority.json", authority)


def parse_feats(value: str) -> dict[str, str]:
    if value == "_":
        return {}
    result: dict[str, str] = {}
    for item in value.split("|"):
        if item.count("=") != 1:
            raise GateFailure("malformed_feats")
        key, val = item.split("=", 1)
        vals = val.split(",")
        if not key or not val or key in result or vals != sorted(set(vals)):
            raise GateFailure("malformed_feats")
        result[key] = val
    if "Number" in result and result["Number"] not in NUMBER:
        raise GateFailure("unknown_number")
    return result


def _normalize_doc_id(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    if ((normalized and normalized[0].isspace() and (not value or value[0] not in " \t"))
            or (normalized and normalized[-1].isspace() and (not value or value[-1] not in " \t"))):
        raise GateFailure("invalid_document_group_whitespace")
    stripped = normalized.strip(" \t")
    if not stripped or "\0" in stripped or "\n" in stripped or "\r" in stripped:
        raise GateFailure("invalid_document_group_id")
    if stripped[0].isspace() or stripped[-1].isspace():
        raise GateFailure("invalid_document_group_whitespace")
    return stripped


def _finish_sentence(partition: str, rows: list[Token], sent_id: str | None,
                     group: str | None, index: int) -> Sentence:
    if not rows or not sent_id or group is None or any(x in sent_id for x in ("\0", "\n", "\r")):
        raise GateFailure("invalid_sentence_identity_or_group")
    if [x.id for x in rows] != list(range(1, len(rows) + 1)):
        raise GateFailure("noncontiguous_token_ids")
    heads = {x.id: x.head for x in rows}
    if sum(x.head == 0 for x in rows) != 1:
        raise GateFailure("root_count")
    for token in rows:
        if token.head not in heads and token.head != 0:
            raise GateFailure("invalid_head")
        seen: set[int] = set()
        cur = token.id
        while cur:
            if cur in seen:
                raise GateFailure("dependency_cycle")
            seen.add(cur)
            cur = heads[cur]
    return Sentence(partition, sent_id, (partition, group), tuple(rows), index)


def parse_conllu_text(text: str, partition: str) -> tuple[list[Sentence], dict[str, int]]:
    rows: list[Token] = []
    sentences: list[Sentence] = []
    sent_id: str | None = None
    current_group: str | None = None
    current_group_count = 0
    groups: set[str] = set()
    seen_ids: set[str] = set()
    counts = {"integer_tokens": 0, "multiword_rows": 0, "empty_node_rows": 0}
    range_end = 0
    empty_node_indices: dict[int, int] = {}

    def flush() -> None:
        nonlocal rows, sent_id, current_group_count, range_end, empty_node_indices
        if not rows and sent_id is None:
            return
        if range_end > len(rows):
            raise GateFailure("malformed_conllu_multiword_span")
        sentence = _finish_sentence(partition, rows, sent_id, current_group, len(sentences))
        if sentence.sent_id in seen_ids:
            raise GateFailure("duplicate_sent_id")
        seen_ids.add(sentence.sent_id)
        sentences.append(sentence)
        current_group_count += 1
        rows = []
        sent_id = None
        range_end = 0
        empty_node_indices = {}

    for line in text.splitlines():
        if not line:
            flush()
            continue
        if line.startswith("#"):
            if line.startswith("# newdoc id = "):
                if rows or sent_id is not None or range_end or empty_node_indices:
                    raise GateFailure("document_group_mid_sentence")
                if current_group is not None and current_group_count == 0:
                    raise GateFailure("empty_document_group")
                group = _normalize_doc_id(line[len("# newdoc id = "):])
                if group in groups:
                    raise GateFailure("duplicate_document_group")
                groups.add(group)
                current_group = group
                current_group_count = 0
            elif line.casefold().lstrip().startswith("# newdoc"):
                raise GateFailure("malformed_document_group_marker")
            elif line.startswith("# sent_id = "):
                if sent_id is not None or rows or range_end or empty_node_indices:
                    raise GateFailure("duplicate_sent_id_comment")
                sent_id = line[len("# sent_id = "):]
            elif line.casefold().lstrip().startswith("# sent_id"):
                raise GateFailure("malformed_sent_id_marker")
            continue
        if current_group is None:
            raise GateFailure("missing_document_group")
        cols = line.split("\t")
        if len(cols) != 10:
            raise GateFailure("malformed_conllu_columns")
        rid = cols[0]
        if "-" in rid:
            if re.fullmatch(r"[1-9][0-9]*-[1-9][0-9]*", rid) is None:
                raise GateFailure("malformed_conllu_row_id")
            first, last = map(int, rid.split("-"))
            if first >= last:
                raise GateFailure("malformed_conllu_row_id")
            if (first != len(rows) + 1 or first <= range_end or not cols[1]
                    or any(cols[i] != "_" for i in (2, 3, 4, 6, 7, 8))
                    or cols[5] not in {"_", "Typo=Yes"}):
                raise GateFailure("malformed_conllu_multiword_row")
            range_end = last
            counts["multiword_rows"] += 1
            continue
        if "." in rid:
            if re.fullmatch(r"[1-9][0-9]*\.[1-9][0-9]*", rid) is None:
                raise GateFailure("malformed_conllu_row_id")
            anchor, node_index = map(int, rid.split("."))
            if (anchor != len(rows) or node_index != empty_node_indices.get(anchor, 0) + 1
                    or cols[6] != "_" or cols[7] != "_" or cols[8] == "_"
                    or not cols[1] or not cols[2] or cols[3] not in UPOS):
                raise GateFailure("malformed_conllu_empty_node_row")
            parse_feats(cols[5])
            empty_node_indices[anchor] = node_index
            counts["empty_node_rows"] += 1
            continue
        if re.fullmatch(r"[1-9][0-9]*", rid) is None:
            raise GateFailure("malformed_conllu_row_id")
        if re.fullmatch(r"0|[1-9][0-9]*", cols[6]) is None:
            raise GateFailure("malformed_integer")
        try:
            tid, head = int(rid), int(cols[6])
        except ValueError as exc:
            raise GateFailure("malformed_integer") from exc
        form, lemma, upos, feats, deprel = cols[1], cols[2], cols[3], cols[5], cols[7]
        if not form or not lemma or upos not in UPOS or not deprel:
            raise GateFailure("missing_or_unknown_field")
        if deprel.split(":", 1)[0] not in DEPREL:
            raise GateFailure("unknown_deprel")
        parse_feats(feats)
        rows.append(Token(tid, unicodedata.normalize("NFC", form), unicodedata.normalize("NFC", lemma), upos, feats, head, deprel))
        counts["integer_tokens"] += 1
    flush()
    if current_group is None or current_group_count == 0 or not sentences:
        raise GateFailure("missing_or_empty_document_groups")
    counts["sentences"] = len(sentences)
    counts["document_groups"] = len(groups)
    return sentences, counts


def parse_conllu(path: Path, partition: str) -> tuple[list[Sentence], dict[str, int]]:
    try:
        text = read_bytes_nofollow(path).decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise GateFailure("conllu_non_utf8:" + partition) from exc
    return parse_conllu_text(text, partition)


def normalized_sentence(sentence: Sentence) -> tuple[str, ...]:
    return tuple(x.casefold() for x in LEX.findall(
        unicodedata.normalize("NFKC", " ".join(token.form for token in sentence.tokens))
    ))


def _cap(form: str) -> str:
    letters = "".join(c for c in form if c.isalpha())
    if not letters:
        return "nonalpha"
    if letters.islower():
        return "lower"
    if letters.isupper():
        return "upper"
    if letters.istitle():
        return "title"
    return "mixed"


def _length(form: str) -> str:
    n = len(unicodedata.normalize("NFC", form))
    return "1" if n == 1 else "2" if n == 2 else "3_4" if n <= 4 else "5_7" if n <= 7 else "8p"


def _depth(token_id: int, heads: dict[int, int]) -> str:
    depth, current = 0, token_id
    while heads[current]:
        current = heads[current]
        depth += 1
    return str(depth) if depth <= 3 else "4p"


def sentence_labels(sentence: Sentence) -> list[dict[str, str | None]]:
    n = len(sentence.tokens)
    heads = {x.id: x.head for x in sentence.tokens}
    result: list[dict[str, str | None]] = []
    for token in sentence.tokens:
        i = token.id
        delta = token.head - i
        head = "ROOT" if token.head == 0 else ("L" if delta < 0 else "R") + (
            "1_2" if abs(delta) <= 2 else "3_4" if abs(delta) <= 4 else "5p"
        )
        boundary = "single" if n == 1 else "initial" if i == 1 else "final" if i == n else "interior"
        feats = parse_feats(token.feats)
        result.append({
            "absolute_bucket": str(min(7, i - 1)),
            "relative_quartile": str(min(3, 4 * (i - 1) // n)),
            "token_identity": unicodedata.normalize("NFKC", token.form).casefold(),
            "lemma_identity": None if token.lemma == "_" else unicodedata.normalize("NFKC", token.lemma).casefold(),
            "capitalization": _cap(token.form),
            "word_length": _length(token.form),
            "punctuation": "PUNCT" if token.form and all(unicodedata.category(c).startswith("P") for c in token.form) else "NONPUNCT",
            "sentence_boundary": boundary,
            "head_signed_distance": head,
            "dependency_depth": _depth(i, heads),
            "upos_coarse": token.upos,
            "deprel_coarse": token.deprel.split(":", 1)[0],
            "number": feats.get("Number"),
        })
    return result


def role_for_group(group_key: tuple[str, str]) -> tuple[str, str, int]:
    digest = sha_bytes(canonical_bytes(["norspan-1/role-v1", COMMIT, list(group_key)]))
    value = int.from_bytes(bytes.fromhex(digest)[:8], "big")
    cuts = (11068046444225730969, 14757395258967641292, 16602069666338596454)
    role = "discovery" if value < cuts[0] else "calibration" if value < cuts[1] else "C1" if value < cuts[2] else "C2"
    return role, digest, value


def license_evidence(raw: bytes | str) -> dict[str, Any]:
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not raw or len(raw) > 131072 or b"\0" in raw:
        return {"status": "ineligible", "reason": "invalid_license_bytes"}
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return {"status": "ineligible", "reason": "invalid_license_utf8"}
    tokens = lexical_tokens(text)
    phrases = [
        ("cc", "by", "sa", "4", "0"),
        ("creative", "commons", "attribution", "sharealike", "4", "0"),
        ("attribution", "sharealike", "4", "0", "international"),
    ]
    negative_phrases = [
        ("all", "rights", "reserved"), ("no", "redistribution"),
        ("non", "commercial", "use", "only"),
    ]
    phrase_count = sum(
        sum(tokens[i:i + len(p)] == p for i in range(len(tokens) - len(p) + 1)) for p in phrases
    )
    negative_phrase_count = sum(
        sum(tokens[i:i + len(p)] == p for i in range(len(tokens) - len(p) + 1)) for p in negative_phrases
    )
    url_chars = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~:/?#[]@!$&'()*+,;=%-")
    accepted_urls = (
        "http://creativecommons.org/licenses/by-sa/4.0",
        "http://creativecommons.org/licenses/by-sa/4.0/",
        "https://creativecommons.org/licenses/by-sa/4.0",
        "https://creativecommons.org/licenses/by-sa/4.0/",
    )
    url_count = 0
    for url in accepted_urls:
        start = 0
        while True:
            at = text.find(url, start)
            if at < 0:
                break
            before = text[at - 1] if at else ""
            after_at = at + len(url)
            after = text[after_at] if after_at < len(text) else ""
            if (not before or before not in url_chars) and (not after or after not in url_chars):
                url_count += 1
            start = at + 1
    contradictory = {"gpl-2.0", "gpl-3.0", "agpl-3.0", "cc-by-nc-4.0", "cc-by-nd-4.0", "proprietary"}
    identifiers = [m.group(1).casefold() for m in LICENSE_ID.finditer(text)]
    contradictory_id_count = sum(item in contradictory for item in identifiers)
    accepted = phrase_count + url_count
    blocked = negative_phrase_count + contradictory_id_count
    return {
        "accepted_phrase_count": phrase_count,
        "accepted_url_count": url_count,
        "contradictory_phrase_count": negative_phrase_count,
        "contradictory_identifier_count": contradictory_id_count,
        "status": "eligible" if accepted > 0 and blocked == 0 else "ineligible",
    }


def deduplicate(sentences: list[Sentence]) -> tuple[list[Sentence], dict[str, Any]]:
    by_norm: dict[tuple[str, ...], list[Sentence]] = collections.defaultdict(list)
    for sentence in sentences:
        by_norm[normalized_sentence(sentence)].append(sentence)
    kept: list[Sentence] = []
    dropped: list[str] = []
    for values in by_norm.values():
        ordered = sorted(values, key=lambda x: (x.partition, x.sent_id))
        kept.append(ordered[0])
        dropped.extend(f"{x.partition}:{x.sent_id}" for x in ordered[1:])
    kept.sort(key=lambda x: (x.partition, x.sent_id))
    return kept, {
        "schema_version": "msae_independent_norspan_v1_dedup_v1",
        "input_count": len(sentences), "retained_count": len(kept),
        "dropped_count": len(dropped), "dropped_ids_sha256": sha_bytes(canonical_bytes(sorted(dropped))),
    }


def history_collisions(sentences: list[Sentence], registry: dict[str, Any], cfg: dict[str, Any]) -> tuple[set[int], dict[str, Any]]:
    candidates = [(s, normalized_sentence(s)) for s in sentences]
    exact: dict[tuple[str, ...], set[int]] = collections.defaultdict(set)
    shorts: dict[int, dict[tuple[str, ...], set[int]]] = collections.defaultdict(lambda: collections.defaultdict(set))
    inverted: dict[tuple[str, ...], set[int]] = collections.defaultdict(set)
    unigrams: dict[str, set[int]] = collections.defaultdict(set)
    for index, (_, tokens) in enumerate(candidates):
        exact[tokens].add(index)
        if len(tokens) <= 9:
            shorts[len(tokens)][tokens].add(index)
        for gram in fivegrams(tokens):
            inverted[gram].add(index)
        for token in set(tokens):
            unigrams[token].add(index)
    implicated: set[int] = set()
    witnesses: list[dict[str, str]] = []
    units = 0
    counts: collections.Counter[str] = collections.Counter()
    for entry in registry["entries"]:
        rel = entry["path"]
        path = ROOT / rel
        if entry["adapter"] not in {"text", "archive"}:
            if entry["sha256"] is not None or entry["extracted_unit_count"] != 0:
                raise GateFailure("history_no_read_disposition:" + rel)
            continue
        expected = (entry["device"], entry["inode"], entry["type"], entry["mode"],
                    entry["nlink"], entry["size"])
        if sha_file(path, expected) != entry["sha256"]:
            raise GateFailure("history_drift:" + rel)
        extracted = 0
        for other in history_units(path, entry["adapter"], cfg, expected):
            extracted += 1
            units += 1
            ids = set(exact.get(other, ()))
            for n, lookup in shorts.items():
                if len(other) > n:
                    for j in range(len(other) - n + 1):
                        ids.update(lookup.get(other[j:j + n], ()))
            if len(other) <= 9 and other:
                ids.update(unigrams.get(other[0], ()))
            for gram in fivegrams(other):
                ids.update(inverted.get(gram, ()))
            for index in sorted(ids):
                sentence, candidate = candidates[index]
                reason = overlap_reason(candidate, other) or overlap_reason(other, candidate)
                if reason:
                    implicated.add(index)
                    counts[reason] += 1
                    if len(witnesses) < 100:
                        witnesses.append({
                            "candidate_id_sha256": sha_bytes(f"{sentence.partition}:{sentence.sent_id}".encode()),
                            "history_path": rel, "reason": reason,
                        })
        if extracted != entry["extracted_unit_count"]:
            raise GateFailure("history_unit_count_drift:" + rel)
    return implicated, {
        "schema_version": "msae_independent_norspan_v1_history_overlap_v1",
        "history_unit_count": units, "implicated_sentence_count": len(implicated),
        "collision_counts": dict(sorted(counts.items())), "witnesses": witnesses,
        "policy_protected_v8_v10_gap": True,
        "status": "eligible_after_deterministic_removal",
    }


def internal_prune(sentences: list[Sentence]) -> tuple[list[Sentence], dict[str, Any]]:
    ordered = sorted(sentences, key=lambda s: (sha_bytes(canonical_bytes(normalized_sentence(s))), s.partition, s.sent_id))
    kept: list[Sentence] = []
    kept_tokens: list[tuple[str, ...]] = []
    dropped: list[tuple[str, str]] = []
    exact: dict[tuple[str, ...], set[int]] = collections.defaultdict(set)
    shorts: dict[int, dict[tuple[str, ...], set[int]]] = collections.defaultdict(lambda: collections.defaultdict(set))
    inverted: dict[tuple[str, ...], set[int]] = collections.defaultdict(set)
    unigrams: dict[str, set[int]] = collections.defaultdict(set)
    for sentence in ordered:
        tokens = normalized_sentence(sentence)
        reason = None
        ids = set(exact.get(tokens, ()))
        for n, lookup in shorts.items():
            if len(tokens) > n:
                for j in range(len(tokens) - n + 1):
                    ids.update(lookup.get(tokens[j:j + n], ()))
        if len(tokens) <= 9 and tokens:
            ids.update(unigrams.get(tokens[0], ()))
        for gram in fivegrams(tokens):
            ids.update(inverted.get(gram, ()))
        for index in sorted(ids):
            other = kept_tokens[index]
            reason = overlap_reason(tokens, other) or overlap_reason(other, tokens)
            if reason:
                break
        if reason:
            dropped.append((f"{sentence.partition}:{sentence.sent_id}", reason))
        else:
            index = len(kept)
            kept.append(sentence)
            kept_tokens.append(tokens)
            exact[tokens].add(index)
            if len(tokens) <= 9:
                shorts[len(tokens)][tokens].add(index)
            for gram in fivegrams(tokens):
                inverted[gram].add(index)
            for token in set(tokens):
                unigrams[token].add(index)
    return kept, {
        "schema_version": "msae_independent_norspan_v1_internal_prune_v1",
        "input_count": len(sentences), "retained_count": len(kept), "dropped_count": len(dropped),
        "dropped_ids_sha256": sha_bytes(canonical_bytes(sorted(x[0] for x in dropped))),
        "reasons": dict(sorted(collections.Counter(x[1] for x in dropped).items())),
    }


def assign_roles(sentences: list[Sentence]) -> tuple[dict[str, list[Sentence]], dict[str, Any]]:
    groups: dict[tuple[str, str], list[Sentence]] = collections.defaultdict(list)
    for sentence in sentences:
        groups[sentence.group_key].append(sentence)
    roles: dict[str, list[Sentence]] = {name: [] for name in ("discovery", "calibration", "C1", "C2")}
    group_counts: collections.Counter[str] = collections.Counter()
    entries: list[dict[str, Any]] = []
    for key in sorted(groups):
        role, digest, value = role_for_group(key)
        roles[role].extend(sorted(groups[key], key=lambda s: s.sent_id))
        group_counts[role] += 1
        entries.append({"group_key_sha256": sha_bytes(canonical_bytes(list(key))), "role": role, "role_digest": digest, "u64": value, "sentence_count": len(groups[key])})
    return roles, {
        "schema_version": "msae_independent_norspan_v1_role_manifest_v1",
        "algorithm": "sha256-canonical-json-u64be-fixed-cutpoints-v1",
        "cutpoints": [11068046444225730969, 14757395258967641292, 16602069666338596454],
        "group_counts": dict(sorted(group_counts.items())),
        "sentence_counts": {role: len(rows) for role, rows in roles.items()},
        "entries": entries,
    }


def cross_role_overlap(roles: dict[str, list[Sentence]]) -> dict[str, Any]:
    names = ("discovery", "calibration", "C1", "C2")
    witnesses: list[dict[str, str]] = []
    counts: collections.Counter[str] = collections.Counter()
    seen: list[tuple[str, Sentence, tuple[str, ...]]] = []
    exact: dict[tuple[str, ...], set[int]] = collections.defaultdict(set)
    shorts: dict[int, dict[tuple[str, ...], set[int]]] = collections.defaultdict(lambda: collections.defaultdict(set))
    inverted: dict[tuple[str, ...], set[int]] = collections.defaultdict(set)
    unigrams: dict[str, set[int]] = collections.defaultdict(set)
    for role in names:
        for sentence in roles[role]:
            tokens = normalized_sentence(sentence)
            ids = set(exact.get(tokens, ()))
            for n, lookup in shorts.items():
                if len(tokens) > n:
                    for j in range(len(tokens) - n + 1):
                        ids.update(lookup.get(tokens[j:j + n], ()))
            if len(tokens) <= 9 and tokens:
                ids.update(unigrams.get(tokens[0], ()))
            for gram in fivegrams(tokens):
                ids.update(inverted.get(gram, ()))
            for index in sorted(ids):
                other_role, other_sentence, other_tokens = seen[index]
                if other_role == role:
                    continue
                reason = overlap_reason(tokens, other_tokens) or overlap_reason(other_tokens, tokens)
                if reason:
                    counts[reason] += 1
                    if len(witnesses) < 100:
                        witnesses.append({
                            "left_role": other_role, "right_role": role,
                            "left_id_sha256": sha_bytes(f"{other_sentence.partition}:{other_sentence.sent_id}".encode()),
                            "right_id_sha256": sha_bytes(f"{sentence.partition}:{sentence.sent_id}".encode()),
                            "reason": reason,
                        })
            index = len(seen)
            seen.append((role, sentence, tokens))
            exact[tokens].add(index)
            if len(tokens) <= 9:
                shorts[len(tokens)][tokens].add(index)
            for gram in fivegrams(tokens):
                inverted[gram].add(index)
            for token in set(tokens):
                unigrams[token].add(index)
    return {
        "schema_version": "msae_independent_norspan_v1_cross_role_overlap_v1",
        "blocking_collision_count": sum(counts.values()),
        "counts": dict(sorted(counts.items())), "witnesses": witnesses,
        "status": "eligible" if not counts else "ineligible",
    }


def public_label(task: str, value: str) -> str:
    if task == "token_identity":
        return sha_bytes(b"norspan-1/token\0" + value.encode("utf-8"))
    if task == "lemma_identity":
        return sha_bytes(b"norspan-1/lemma\0" + value.encode("utf-8"))
    return value


def support_report(roles: dict[str, list[Sentence]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    all_role = set(TASKS)
    for role, sentences in roles.items():
        tasks: dict[str, Any] = {}
        role_eligible: set[str] = set()
        for task in TASKS:
            classes: dict[str, set[str]] = collections.defaultdict(set)
            for sentence in sentences:
                sid = f"{sentence.partition}:{sentence.sent_id}"
                for labels in sentence_labels(sentence):
                    value = labels[task]
                    if value is not None:
                        classes[str(value)].add(sid)
            retained = {public_label(task, label): len(ids) for label, ids in classes.items() if len(ids) >= 20}
            eligible = len(retained) >= 2
            if eligible:
                role_eligible.add(task)
            tasks[task] = {"eligible": eligible, "retained_class_count": len(retained), "distinct_sentences_by_class": dict(sorted(retained.items()))}
        all_role &= role_eligible
        output[role] = {"sentence_count": len(sentences), "tasks": tasks}
    passed = REQUIRED <= all_role and len(OPTIONAL & all_role) >= 2
    return {
        "schema_version": "msae_independent_norspan_v1_support_v1",
        "distinct_sentence_floor": 20, "roles": output,
        "all_role_task_intersection": sorted(all_role),
        "required_tasks": sorted(REQUIRED), "optional_tasks": sorted(OPTIONAL),
        "status": "eligible" if passed else "ineligible",
    }


def token_objects(sentence: Sentence) -> list[dict[str, Any]]:
    return [dataclasses.asdict(token) for token in sentence.tokens]


def render_role_payloads(roles: dict[str, list[Sentence]]) -> dict[str, bytes]:
    rendered: dict[str, bytes] = {}
    for role in ("discovery", "calibration", "C1", "C2"):
        chunks: list[bytes] = []
        for sentence in roles[role]:
            _, group_digest, _ = role_for_group(sentence.group_key)
            record = {
                "schema_version": "msae_independent_norspan_v1_payload_v1",
                "source_repo": REPO, "source_commit": COMMIT,
                "role": role, "upstream_partition": sentence.partition,
                "sent_id": sentence.sent_id,
                "group_key": list(sentence.group_key), "group_role_digest": group_digest,
                "tokens": token_objects(sentence),
            }
            chunks.append(canonical_file_bytes(record))
        rendered[role] = b"".join(chunks)
    return rendered


def publish_private_roles(roles: dict[str, list[Sentence]]) -> dict[str, Any]:
    """Hold every role's original writer through final aggregate qualification."""
    ensure_directory(DATA, 0o700)
    result = jpc_runtime.publish_role_pairs(PRIVATE, render_role_payloads(roles))
    session = _PAIR_SESSION.get()
    if session is not None:
        session.private_manifest = result
        session.checkpoint()
    return {role: {**item, "record_count": len(roles[role]),
                   "custody_hash_open_count": 0, "scientific_open_count": 0}
            for role, item in result.items()}


def verify_private_payload_bytes(rendered: dict[str, bytes], *, expected_manifest=None) -> dict[str, dict[str, Any]]:
    if type(rendered) is not dict or set(rendered) != set(jpc_runtime.ROLES) or any(type(v) is not bytes for v in rendered.values()):
        raise GateFailure("private_rendered_role_schema")
    if type(expected_manifest) is not dict or set(expected_manifest) != set(jpc_runtime.ROLES):
        raise GateFailure("outside_private_manifest_required")
    manifests = {role:{key:item[key] for key in ["sha256","bytes","mode","nlink","pair"]}
                 for role,item in expected_manifest.items()}
    verified = jpc_runtime.verify_role_pairs(PRIVATE,manifests)
    result = {}
    for role,expected in rendered.items():
        actual = verified[role]
        if actual["sha256"] != sha_bytes(expected) or actual["bytes"] != len(expected):
            raise GateFailure("private_payload_drift:"+role)
        result[role] = {"sha256":actual["sha256"],"bytes":actual["bytes"],"record_count":expected.count(b"\n"),
                        "custody_hash_open_count":1,"scientific_open_count":0}
    return result


def _rejection(code: str, prefix: list[str]) -> None:
    inv = protocol_inventory()
    actual = [name for name in SCIENCE_PREFIX if name in set(inv["public"])]
    if actual != prefix or actual != list(SCIENCE_PREFIX[:len(actual)]):
        raise GateFailure("rejection_nonprefix_state")
    if inv["private_files"] or "private" in inv["data_dirs"]:
        raise GateFailure("rejection_after_private_unresolved")
    publish_json(PROV / "rejection.json", {
        "schema_version": "msae_independent_norspan_v1_rejection_v1",
        "status": "rejected_after_scientific_entry",
        "failure_code": code, "published_scientific_prefix": actual,
        "public_artifacts": {name: sha_file(PROV / name) for name in actual},
        "raw_access_started_sha256": sha_file(PROV / "raw_access_started.json"),
        "source_acquisition_sha256": sha_file(PROV / "source_acquisition.json"),
        "evidence": evidence_snapshot(),
        "model_operations": 0, "gpu_queries": 0, "training_runs": 0,
        "next_action": "new_reviewed_protocol_only",
    })


def history_snapshot_paths(state: str, inv: dict[str, Any]) -> set[str]:
    """Literal cumulative rows; never grant an entire directory prefix."""
    names = {"current_history_registry.json", "baseline.json"}
    stages = [
        ("authority", "authority.json"), ("acquisition_entered", "acquisition_entry.json"),
        ("network_ready", "pre_network_ready.json"), ("network_started", "network_started.json"),
        ("acquisition_terminal", "source_acquisition.json"),
        ("scientific_entered", "scientific_entry.json"), ("raw_ready", "pre_raw_ready.json"),
        ("raw_started", "raw_access_started.json"),
    ]
    order = ["clean_reviewed", "baseline", *(stage for stage, _ in stages), "scientific_terminal"]
    if state not in order:
        raise GateFailure("history_snapshot_state")
    if state == "clean_reviewed":
        return set()
    for stage, name in stages:
        if order.index(state) >= order.index(stage):
            names.add(name)
    if state in {"acquisition_terminal", "scientific_terminal"} and "rejection.json" in inv["public"] and "source_acquisition.json" not in inv["public"]:
        names = set(inv["public"]) if state == "scientific_terminal" else names - {"source_acquisition.json"} | {"rejection.json"}
    if state == "scientific_terminal":
        names = set(inv["public"])
    paths = {(PROV / alias).relative_to(ROOT).as_posix()
             for name in names for alias in [name,"."+name+".stage"]}
    if order.index(state) >= order.index("authority"):
        paths.add("reports/adversarial/msae_independent_norspan_v1_authority_review.md")
    if order.index(state) >= order.index("acquisition_terminal") and inv["data_root"] is not None:
        paths.add(DATA.relative_to(ROOT).as_posix())
    for path in list(paths):
        parent = PurePosixPath(path).parent
        while parent.as_posix() != ".":
            paths.add(parent.as_posix()); parent = parent.parent
    return paths



def names_from_inventory(inv):
    return set(inv["public"]) & PHASE_PUBLIC

def validate_history_registry(registry: dict[str, Any], cfg: dict[str, Any], *,
                              at_state: str | None = None) -> dict[str, Any]:
    fields = {'schema_version','temporal_scope','protected_v8_v10_content_gap','protected_content_reads',
              'entries','entry_count','disposition_counts','alias_occurrences','candidate_identifier_hashes',
              'blocking_alias_occurrence_count','allowed_authority_paths','status'}
    if type(registry) is not dict or set(registry) != fields:
        raise GateFailure('history_registry_exact_schema')
    require_literals(registry,{'temporal_scope':'all_policy_accessible_current_history_before_acquisition',
        'protected_v8_v10_content_gap':True,'protected_content_reads':0,'blocking_alias_occurrence_count':0,
        'allowed_authority_paths':sorted(ALLOWED_AUTHORITY_PATHS),'status':'eligible',
        'candidate_identifier_hashes':[pedigree_hash(seq) for seq in ALIAS_SEQUENCES]},'history_registry_literals')
    if registry.get("schema_version") != "msae_independent_norspan_v1_current_history_registry_v1":
        raise GateFailure("history_registry_schema")
    entries = registry.get("entries")
    if not isinstance(entries, list) or type(registry.get('entry_count')) is not int or registry.get("entry_count") != len(entries):
        raise GateFailure("history_registry_count")
    paths = [entry.get("path") for entry in entries]
    if any(not isinstance(path, str) or PurePosixPath(path).is_absolute()
           or ".." in PurePosixPath(path).parts for path in paths):
        raise GateFailure("history_registry_path")
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise GateFailure("history_registry_order")
    inv = protocol_inventory()
    state = classify_protocol_state()
    allowed = history_snapshot_paths(state, inv)
    snapshot_state = at_state or state
    snapshot_paths = history_snapshot_paths(snapshot_state, inv)
    frozen = {entry["path"]: entry for entry in entries}
    seen: set[str] = set()
    added: list[dict[str, Any]] = []
    fields = {"path", "device", "inode", "type", "mode", "nlink", "size",
              "sha256", "adapter", "extracted_unit_count"}
    with _history_census() as census:
        for rel, path, st, disposition in census:
            seen.add(rel)
            if rel not in frozen:
                if rel not in allowed:
                    raise GateFailure("history_unexpected_addition:" + rel)
                digest = None
                if disposition == "candidate_regular":
                    paired_name = None
                    if path.parent == PROV:
                        for logical in names_from_inventory(inv):
                            if path.name in {logical,"."+logical+".stage"}:
                                paired_name = logical
                                break
                    if paired_name is not None:
                        receipt = _expected_session().expected(paired_name)
                        jumbo_pair._check_stat(st,receipt,2)
                        digest = _expected_session().digest(paired_name)["sha256"]
                    else:
                        if stat.S_IMODE(st.st_mode) != 0o644 or st.st_nlink != 1:
                            raise GateFailure("history_added_control_metadata:" + rel)
                        digest = sha_file(path, st)
                elif not stat.S_ISDIR(st.st_mode):
                    raise GateFailure("history_added_control_type:" + rel)
                if rel in snapshot_paths:
                    added.append({"path": rel, "type": stat.S_IFMT(st.st_mode),
                                  "mode": stat.S_IMODE(st.st_mode), "sha256": digest})
                continue
            entry = frozen[rel]
            if set(entry) != fields:
                raise GateFailure("history_entry_schema:" + rel)
            expected = (entry["device"], entry["inode"], entry["type"], entry["mode"], entry["nlink"], entry["size"])
            compare_length = 4 if stat.S_ISDIR(st.st_mode) else 6
            if _identity(st)[:compare_length] != expected[:compare_length]:
                raise GateFailure("history_metadata_drift:" + rel)
            adapter = classify_file(path, st) if disposition == "candidate_regular" else disposition
            if adapter != entry["adapter"]:
                raise GateFailure("history_disposition_drift:" + rel)
            if adapter in {"text", "archive"}:
                if sha_file(path, st) != entry["sha256"]:
                    raise GateFailure("history_hash_drift:" + rel)
                count = sum(1 for _ in history_units(path, adapter, cfg, st))
                if count != entry["extracted_unit_count"]:
                    raise GateFailure("history_unit_count_drift:" + rel)
            elif entry["sha256"] is not None or entry["extracted_unit_count"] != 0:
                raise GateFailure("history_protected_read_claim:" + rel)
    if set(frozen) - seen:
        raise GateFailure("history_missing:" + sorted(set(frozen) - seen)[0])
    added.sort(key=lambda row: row["path"])
    return {"state": snapshot_state, "baseline_entry_count": len(entries),
            "frozen_entries_sha256": sha_bytes(canonical_bytes(entries)),
            "added_paths_sha256": sha_bytes(canonical_bytes(added)),
            "added_path_count": len(added), "protected_content_reads": 0}


CONTROL_FIELDS = {
    "baseline.json": "schema_version current_history_registry_sha256 config_sha256 implementation_review_sha256 git_head evidence source_namespace_absent_at_registry_start model_operations gpu_queries training_runs status".split(),
    "authority.json": "schema_version source_repo source_commit source_files baseline_sha256 current_history_registry_sha256 controls pre_authority_evidence pre_authority_history_census absent_at_publication model_operations gpu_queries training_runs status".split(),
    "acquisition_entry.json": "schema_version source_repo source_commit source_files baseline_sha256 history_registry_sha256 authority_sha256 authority_review_sha256 runner_sha256 authority_controls state_order pre_entry_inventory expected_absent expected_schemas scratch_binding entry_lineage_sha256 pre_entry_evidence pre_entry_history_census subprocesses_started model_operations gpu_queries training_runs status".split(),
    "pre_network_ready.json": "schema_version acquisition_entry_sha256 scratch_binding evidence history_census status".split(),
    "network_started.json": "schema_version pre_network_ready_sha256 scratch_binding evidence history_census status".split(),
    "scientific_entry.json": "schema_version source_acquisition_sha256 history_registry_sha256 config_sha256 pre_entry_evidence pre_entry_history_census raw_accesses_before_entry model_operations gpu_queries training_runs status".split(),
    "pre_raw_ready.json": "schema_version scientific_entry_sha256 evidence history_census status".split(),
    "raw_access_started.json": "schema_version pre_raw_ready_sha256 evidence history_census status".split(),
}


def require_literals(record: dict[str, Any], values: dict[str, Any], code: str) -> None:
    for key, expected in values.items():
        if key not in record or canonical_bytes(record[key]) != canonical_bytes(expected):
            raise GateFailure(code + ":" + key)


def canonical_control(path: Path, keys: Iterable[str] | None = None) -> dict[str, Any]:
    raw = read_bytes_nofollow(path, mode=0o644, nlink=2 if _paired_control_name(path) is not None else 1)
    record = parse_json_bytes(raw, path)
    if not isinstance(record, dict) or raw != canonical_file_bytes(record):
        raise GateFailure("noncanonical_control:" + path.name)
    if keys is not None and set(record) != set(keys):
        raise GateFailure("control_schema:" + path.name)
    return record


def control_record(name: str) -> dict[str, Any]:
    return canonical_control(PROV / name, CONTROL_FIELDS[name])


def control_manifest(rel: str, mode: int) -> dict[str, Any]:
    path = ROOT / rel
    if _paired_control_name(path) is not None:
        return _expected_session().digest(path.name)
    observed = stream_file_digest(path, mode=mode, nlink=1)
    return {"sha256": observed["sha256"], "mode": mode, "nlink": 1}


def validate_evidence(evidence: dict[str, Any]) -> None:
    keys = {"process", "training", "porcelain", "model_operations", "gpu_queries", "training_runs"}
    if not isinstance(evidence, dict) or set(evidence) != keys:
        raise GateFailure("evidence_schema")
    require_literals(evidence, {"model_operations": 0, "gpu_queries": 0, "training_runs": 0}, "evidence_operations")
    process = evidence["process"]
    if (not isinstance(process, dict) or set(process) != {"scanned_process_count", "prohibited_match_count", "matches"}
            or type(process["scanned_process_count"]) is not int or process["scanned_process_count"] < 1):
        raise GateFailure("evidence_process_schema")
    require_literals(process, {"prohibited_match_count": 0, "matches": []}, "evidence_prohibited_process")
    for name, count_key, hash_key in [("training", "entry_count", "manifest_sha256"),
                                       ("porcelain", "outside_protocol_count", "outside_protocol_sha256")]:
        value = evidence[name]
        if (not isinstance(value, dict) or set(value) != {count_key, hash_key}
                or type(value[count_key]) is not int or value[count_key] < 0
                or not isinstance(value[hash_key], str) or re.fullmatch(r"[0-9a-f]{64}", value[hash_key]) is None):
            raise GateFailure("evidence_" + name + "_schema")


def validate_baseline_chain():
    cfg = load_config()
    baseline = control_record("baseline.json")
    registry = canonical_control(PROV / "current_history_registry.json")
    implementation = canonical_implementation_review_path()
    if not review_is_ship(implementation):
        raise GateFailure('implementation_review_not_ship')
    require_literals(baseline, {
        "schema_version": "msae_independent_norspan_v1_baseline_v1",
        "current_history_registry_sha256": sha_file(PROV / "current_history_registry.json"),
        "config_sha256": sha_file(CONFIG_PATH), "implementation_review_sha256": sha_file(implementation),
        "git_head": git_head(), "source_namespace_absent_at_registry_start": True,
        "model_operations": 0, "gpu_queries": 0, "training_runs": 0, "status": "eligible",
    }, "authority_baseline")
    validate_history_registry(registry,cfg)
    current = evidence_snapshot()
    validate_evidence(baseline['evidence']);validate_evidence(current)
    evidence_compatible(baseline['evidence'],current)
    return cfg,baseline,registry


def validate_authority_chain(review_sha256: str | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    cfg,baseline,registry = validate_baseline_chain()
    authority = control_record('authority.json')
    review = canonical_authority_review_path()
    if not review_is_ship(review):
        raise GateFailure('authority_review_not_ship')
    review_digest = stream_file_digest(review,mode=0o644,nlink=1)['sha256']
    if review_sha256 is not None and review_digest != review_sha256:
        raise GateFailure('authority_review_hash')
    controls = {rel: control_manifest(rel, mode) for rel, mode in AUTHORITY_CONTROL_MODES.items()}
    require_literals(authority, {
        "schema_version": "msae_independent_norspan_v1_authority_v1",
        "source_repo": REPO, "source_commit": COMMIT, "source_files": [*SOURCE_FILES.values(), LICENSE_FILE],
        "baseline_sha256": sha_file(PROV / "baseline.json"),
        "current_history_registry_sha256": sha_file(PROV / "current_history_registry.json"),
        "controls": controls, "absent_at_publication": sorted(ALLOWED_AUTHORITY_PATHS - set(AUTHORITY_CONTROL_MODES)),
        "model_operations": 0, "gpu_queries": 0, "training_runs": 0,
        "status": "awaiting_independent_authority_review",
        "pre_authority_history_census": validate_history_registry(registry, cfg, at_state="baseline"),
    }, "authority")
    for evidence in [baseline["evidence"], authority["pre_authority_evidence"], evidence_snapshot()]:
        validate_evidence(evidence); evidence_compatible(baseline["evidence"], evidence)
    validate_phase_records(cfg, baseline, authority, registry, review_digest)
    return cfg, baseline, authority, registry


def validate_phase_records(cfg: dict[str, Any], baseline: dict[str, Any], authority: dict[str, Any],
                           registry: dict[str, Any], review_digest: str) -> None:
    paths = set(protocol_inventory()["public"])
    for name, previous_state, status, schema, bindings in [
        ("acquisition_entry.json", "authority", "entered", "acquisition_entry", {
            "baseline_sha256": "baseline.json", "history_registry_sha256": "current_history_registry.json", "authority_sha256": "authority.json"}),
        ("pre_network_ready.json", "acquisition_entered", "ready", "pre_network_ready", {"acquisition_entry_sha256": "acquisition_entry.json"}),
        ("network_started.json", "network_ready", "started", "network_started", {"pre_network_ready_sha256": "pre_network_ready.json"}),
        ("scientific_entry.json", "acquisition_terminal", "entered", "scientific_entry", {"source_acquisition_sha256": "source_acquisition.json", "history_registry_sha256": "current_history_registry.json"}),
        ("pre_raw_ready.json", "scientific_entered", "ready", "pre_raw_ready", {"scientific_entry_sha256": "scientific_entry.json"}),
        ("raw_access_started.json", "raw_ready", "started", "raw_access_started", {"pre_raw_ready_sha256": "pre_raw_ready.json"}),
    ]:
        if name not in paths:
            continue
        record = control_record(name)
        expected = {"schema_version": "msae_independent_norspan_v1_" + schema + ("_jpc_v1" if name in {"acquisition_entry.json","pre_network_ready.json","network_started.json"} else "_v1"), "status": status,
                    **{field: sha_file(PROV / predecessor) for field, predecessor in bindings.items()}}
        census_key = "pre_entry_history_census" if status == "entered" else "history_census"
        expected[census_key] = validate_history_registry(registry, cfg, at_state=previous_state)
        if status == "entered":
            expected.update({"model_operations": 0, "gpu_queries": 0, "training_runs": 0})
        if name in {"acquisition_entry.json","pre_network_ready.json","network_started.json"}:
            entry = record if name == "acquisition_entry.json" else control_record("acquisition_entry.json")
            binding = entry["scratch_binding"]
            jpc_runtime._validate_scratch_binding(binding)
            require_literals(binding,{"authority_sha256":sha_file(PROV/"authority.json"),
                                      "entry_lineage_sha256":entry["entry_lineage_sha256"]},"phase_scratch_lineage")
            expected["scratch_binding"] = binding
        if name == "acquisition_entry.json":
            seed = {"authority_sha256":sha_file(PROV/"authority.json"),"baseline_sha256":sha_file(PROV/"baseline.json"),
                    "history_registry_sha256":sha_file(PROV/"current_history_registry.json"),
                    "runner_sha256":sha_file(ROOT/"scripts/acquire_msae_independent_norspan_v1.py"),
                    "source_commit":COMMIT,"source_files":[*SOURCE_FILES.values(),LICENSE_FILE]}
            expected["entry_lineage_sha256"] = sha_bytes(canonical_bytes(seed))
            expected.update({"source_repo": REPO, "source_commit": COMMIT, "source_files": [*SOURCE_FILES.values(), LICENSE_FILE],
                             "authority_review_sha256": review_digest, "authority_controls": authority["controls"],
                             "runner_sha256": authority["controls"]["scripts/acquire_msae_independent_norspan_v1.py"]["sha256"],
                             "state_order": cfg["state_order"], "expected_absent": authority["absent_at_publication"],
                             "expected_schemas": {"entry": "msae_independent_norspan_v1_acquisition_entry_jpc_v1", "network_ready": "msae_independent_norspan_v1_pre_network_ready_jpc_v1", "network_started": "msae_independent_norspan_v1_network_started_jpc_v1", "terminal": "msae_independent_norspan_v1_source_acquisition_jpc_v1"},
                             "subprocesses_started": 0})
            inv = protocol_inventory()
            old_names = {"current_history_registry.json", "baseline.json", "authority.json"}
            inv["public"] = sorted(old_names)
            inv["public_manifest"] = [row for row in inv["public_manifest"] if row["path"] in old_names | {"."+name+".stage" for name in old_names}]
            inv["data_root"] = None
            for field in ["data_dirs", "data_files", "data_other", "raw_files", "private_files", "data_manifest"]:
                inv[field] = []
            expected["pre_entry_inventory"] = inv
        if name == "scientific_entry.json":
            expected.update({"config_sha256": sha_file(CONFIG_PATH), "raw_accesses_before_entry": 0})
        require_literals(record, expected, "phase_record:" + name)
        evidence = record["pre_entry_evidence" if status == "entered" else "evidence"]
        validate_evidence(evidence); evidence_compatible(baseline["evidence"], evidence)


COMMAND_NAMES = ["clone", "sparse_init", "sparse_set", "checkout", "head", "tree", "ls_tree", "object_inventory"]


def validate_command_chain(commands: Any, cfg: dict[str, Any], *, rejection: bool = False) -> None:
    """Reconstruct literal commands and bounded observations, never execute them."""
    if (not isinstance(commands, list) or not commands or len(commands) > len(COMMAND_NAMES)
            or (not rejection and len(commands) != len(COMMAND_NAMES))):
        raise GateFailure("acquisition_command_count")
    fields = {"name", "argv", "exit_status", "stdout_bytes", "stdout_sha256",
              "stderr_bytes", "stderr_sha256", "supervision_failure"}
    limits = cfg["acquisition_limits"]
    for i, row in enumerate(commands):
        if (not isinstance(row, dict) or set(row) != fields or row["name"] != COMMAND_NAMES[i]
                or type(row["exit_status"]) is not int
                or row["supervision_failure"] not in {None, "timeout", "stdout_limit", "stderr_limit"}
                or not isinstance(row["argv"], list) or not all(isinstance(a, str) for a in row["argv"])):
            raise GateFailure("acquisition_command_schema")
        for stream in ["stdout", "stderr"]:
            count, digest = row[stream + "_bytes"], row[stream + "_sha256"]
            if (type(count) is not int or not 0 <= count <= limits[stream + "_limit_bytes"]
                    or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                    or (count == 0 and digest != sha_bytes(b""))):
                raise GateFailure("acquisition_command_observation")
        failed = row["exit_status"] != 0 or row["supervision_failure"] is not None
        if failed != (rejection and i == len(commands) - 1):
            raise GateFailure("acquisition_command_disposition")
        if row["supervision_failure"] in {"stdout_limit", "stderr_limit"}:
            stream = row["supervision_failure"].split("_")[0]
            if row[stream + "_bytes"] != limits[stream + "_limit_bytes"]:
                raise GateFailure("acquisition_output_limit_observation")
    clone = commands[0]["argv"]
    base = ["git", "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null"]
    if (len(clone) != len(base) + 6
            or clone[:-2] != [*base, "clone", "--quiet", "--filter=blob:none", "--no-checkout"]
            or clone[-2] != REPO or not Path(clone[-1]).is_absolute()
            or Path(clone[-1]).name != "repo"):
        raise GateFailure("acquisition_clone_argv")
    repo = clone[-1]
    expected = [clone,
        [*base, "-C", repo, "sparse-checkout", "init", "--no-cone"],
        [*base, "-C", repo, "sparse-checkout", "set", "--no-cone", *SOURCE_FILES.values(), LICENSE_FILE],
        [*base, "-C", repo, "checkout", "--quiet", "--detach", COMMIT],
        [*base, "-C", repo, "rev-parse", "HEAD"],
        [*base, "-C", repo, "rev-parse", COMMIT + "^{tree}"],
        [*base, "-C", repo, "ls-tree", "-z", COMMIT, "--", *SOURCE_FILES.values(), LICENSE_FILE],
        [*base, "-C", repo, "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
    ]
    if [row["argv"] for row in commands] != expected[:len(commands)]:
        raise GateFailure("acquisition_exact_argv")

def validate_scratch_record(record: Any) -> None:
    keys = {"schema_version","binding","retained","cleanup_attempts","current_fsync_completed",
            "entries","total_bytes","budget_monitor_is_hard_quota","observation_contract",
            "retained_object_count","server_backup_guarantees"}
    if type(record) is not dict or set(record) != keys:
        raise GateFailure("acquisition_scratch_schema")
    require_literals(record,{"schema_version":"norspan_jpc_retained_scratch_v1","retained":True,
                            "cleanup_attempts":0,"current_fsync_completed":True,
                            "budget_monitor_is_hard_quota":False,
                            "observation_contract":"controlled_writer_multi_observation_not_atomic",
                            "server_backup_guarantees":"UNKNOWN"},"acquisition_retained_scratch")
    try:
        jpc_runtime._validate_scratch_binding(record["binding"])
    except jpc_runtime.RuntimeBlocked as exc:
        raise GateFailure(str(exc)) from exc
    for key,limit,minimum in [("entries",65536,0),("total_bytes",jpc_runtime.TOTAL_BYTES_LIMIT,0),("retained_object_count",1024,1)]:
        if type(record[key]) is not int or not minimum <= record[key] <= limit:
            raise GateFailure("acquisition_scratch_budget:"+key)
    if record["retained_object_count"] != record["entries"] + 1:
        raise GateFailure("acquisition_scratch_object_count")


def validate_acquisition_metadata(acquisition: dict[str, Any], cfg: dict[str, Any]) -> bytes:
    """Replay typed source-free metadata, never trust counters without observations."""
    require_literals(acquisition, {
        "schema_version": "msae_independent_norspan_v1_source_acquisition_jpc_v1",
        "status": "success", "source_repo": REPO, "source_commit": COMMIT,
        "sparse_checkout": True, "worktree_exact_four_files": True,
        "source_content_printed": False, "model_operations": 0,
        "gpu_queries": 0, "training_runs": 0,
    }, "acquisition_literals")
    validate_scratch_record(acquisition["scratch"])
    if (acquisition["scratch"]["binding"]["authority_sha256"] != acquisition["authority_sha256"]
            or acquisition["scratch"]["binding"] != control_record("acquisition_entry.json")["scratch_binding"]):
        raise GateFailure("acquisition_scratch_entry_binding")
    files = acquisition["files"]
    if not isinstance(files, dict) or set(files) != {*SOURCE_FILES.values(), LICENSE_FILE}:
        raise GateFailure("acquisition_file_set")
    for row in files.values():
        if (not isinstance(row, dict) or set(row) != {"sha256", "bytes", "mode", "nlink", "pair", "git_blob_sha1"}
                or type(row["bytes"]) is not int or row["bytes"] < 0
                or not isinstance(row["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
                or not isinstance(row["git_blob_sha1"], str) or re.fullmatch(r"[0-9a-f]{40}", row["git_blob_sha1"]) is None):
            raise GateFailure("acquisition_file_schema")
        require_literals(row, {"mode": 0o444, "nlink": 2}, "acquisition_file_custody")
        name = next(name for name,value in files.items() if value is row)
        jpc_runtime._expected_receipt(RAW/name,{key:row[key] for key in ["sha256","bytes","mode","nlink","pair"]},0o444)
    if (not isinstance(acquisition["tree_object_sha1"], str)
            or re.fullmatch(r"[0-9a-f]{40}", acquisition["tree_object_sha1"]) is None):
        raise GateFailure("acquisition_tree_oid")
    records = acquisition["local_object_records"]
    if (not isinstance(records, list) or not records
            or len(records) > cfg["acquisition_limits"]["stdout_limit_bytes"] // 44):
        raise GateFailure("acquisition_object_records")
    objects = {}; counts = {}; lines = []
    for row in records:
        if (not isinstance(row, dict) or set(row) != {"oid", "kind", "bytes"}
                or not isinstance(row["oid"], str) or re.fullmatch(r"[0-9a-f]{40}", row["oid"]) is None
                or not isinstance(row["kind"], str) or row["kind"] not in {"blob", "tree", "commit", "tag"}
                or type(row["bytes"]) is not int or row["bytes"] < 0 or row["oid"] in objects):
            raise GateFailure("acquisition_object_record_schema")
        objects[row["oid"]] = (row["kind"], row["bytes"])
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1
        lines.append(f"{row['oid']} {row['kind']} {row['bytes']}\n".encode("ascii"))
    require_literals(acquisition, {
        "local_object_type_counts": dict(sorted(counts.items())),
        "local_blob_object_ids": sorted(oid for oid, (kind, _size) in objects.items() if kind == "blob"),
    }, "acquisition_object_derived_metadata")
    if (objects.get(COMMIT, (None, 0))[0] != "commit"
            or objects.get(acquisition["tree_object_sha1"], (None, 0))[0] != "tree"
            or set(acquisition["local_blob_object_ids"]) != {row["git_blob_sha1"] for row in files.values()}
            or any(objects.get(row["git_blob_sha1"]) != ("blob", row["bytes"]) for row in files.values())):
        raise GateFailure("acquisition_object_file_binding")
    payload = b"".join(lines)
    if len(payload) > cfg["acquisition_limits"]["stdout_limit_bytes"]:
        raise GateFailure("acquisition_object_inventory_bound")
    return payload


def validate_control_chain() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    current_state = classify_protocol_state()
    if current_state not in {"acquisition_terminal", "scientific_entered", "raw_ready",
                              "scientific_terminal", "raw_started"}:
        raise GateFailure("scientific_pre_state")
    cfg, baseline, authority, registry = validate_authority_chain()
    acquisition = canonical_control(PROV / "source_acquisition.json")
    entry = load_json(PROV / "acquisition_entry.json")
    network_ready = load_json(PROV / "pre_network_ready.json")
    network_started = load_json(PROV / "network_started.json")
    registry = load_json(PROV / "current_history_registry.json")
    expected_acquisition_keys = {
        "schema_version", "source_repo", "source_commit", "tree_object_sha1",
        "tree_listing_sha256", "files", "commands", "minimal_environment_keys",
        "minimal_environment", "local_blob_object_ids", "local_object_type_counts", "local_object_records",
        "sparse_checkout", "worktree_exact_four_files", "scratch",
        "source_content_printed", "authority_sha256", "authority_review_sha256",
        "acquisition_entry_sha256", "post_acquisition_evidence", "model_operations",
        "gpu_queries", "training_runs", "status",
    }
    if set(acquisition) != expected_acquisition_keys \
            or acquisition.get("schema_version") != "msae_independent_norspan_v1_source_acquisition_jpc_v1" \
            or acquisition.get("status") != "success" \
            or acquisition.get("source_repo") != REPO or acquisition.get("source_commit") != COMMIT:
        raise GateFailure("acquisition_schema")
    object_inventory = validate_acquisition_metadata(acquisition, cfg)
    require_literals(entry, {"model_operations": 0, "gpu_queries": 0, "training_runs": 0},
                     "acquisition_entry_operation_count")
    if network_ready.get("schema_version") != "msae_independent_norspan_v1_pre_network_ready_jpc_v1" \
            or network_ready.get("status") != "ready" \
            or network_started.get("schema_version") != "msae_independent_norspan_v1_network_started_jpc_v1" \
            or network_started.get("status") != "started":
        raise GateFailure("acquisition_marker_schema")
    if baseline.get("current_history_registry_sha256") != sha_file(PROV / "current_history_registry.json"):
        raise GateFailure("baseline_registry_hash")
    if authority.get("baseline_sha256") != sha_file(PROV / "baseline.json"):
        raise GateFailure("authority_baseline_hash")
    if authority.get("current_history_registry_sha256") != sha_file(PROV / "current_history_registry.json"):
        raise GateFailure("authority_registry_hash")
    controls = authority.get("controls", {})
    if set(controls) != set(AUTHORITY_CONTROL_MODES):
        raise GateFailure("authority_control_set")
    for rel, expected_mode in AUTHORITY_CONTROL_MODES.items():
        path = ROOT / rel
        if controls[rel] != control_manifest(rel, expected_mode):
            raise GateFailure("authority_control_drift:" + rel)
    if acquisition.get("authority_sha256") != sha_file(PROV / "authority.json"):
        raise GateFailure("acquisition_authority_hash")
    if acquisition.get("acquisition_entry_sha256") != sha_file(PROV / "acquisition_entry.json"):
        raise GateFailure("acquisition_entry_hash")
    if network_ready.get("acquisition_entry_sha256") != sha_file(PROV / "acquisition_entry.json") \
            or network_started.get("pre_network_ready_sha256") != sha_file(PROV / "pre_network_ready.json"):
        raise GateFailure("acquisition_marker_lineage")
    if entry.get("authority_sha256") != sha_file(PROV / "authority.json") \
            or entry.get("baseline_sha256") != sha_file(PROV / "baseline.json") \
            or entry.get("history_registry_sha256") != sha_file(PROV / "current_history_registry.json"):
        raise GateFailure("acquisition_entry_lineage")
    if entry.get("authority_controls") != controls or entry.get("state_order") != cfg["state_order"]:
        raise GateFailure("acquisition_entry_authority")
    for evidence in (entry.get("pre_entry_evidence"), network_ready.get("evidence"),
                     network_started.get("evidence"), acquisition.get("post_acquisition_evidence")):
        if not isinstance(evidence, dict):
            raise GateFailure("acquisition_evidence_schema")
        validate_evidence(evidence)
        evidence_compatible(baseline["evidence"], evidence)
    if (PROV / "scientific_entry.json").exists():
        scientific_entry = load_json(PROV / "scientific_entry.json")
        if (scientific_entry.get("source_acquisition_sha256") != sha_file(PROV / "source_acquisition.json")
                or scientific_entry.get("history_registry_sha256") != sha_file(PROV / "current_history_registry.json")
                or scientific_entry.get("config_sha256") != sha_file(CONFIG_PATH)):
            raise GateFailure("scientific_marker_lineage")
        science_evidence = [scientific_entry.get("pre_entry_evidence")]
        if current_state in {"raw_ready", "scientific_terminal"}:
            pre_raw = load_json(PROV / "pre_raw_ready.json")
            if pre_raw.get("scientific_entry_sha256") != sha_file(PROV / "scientific_entry.json"):
                raise GateFailure("scientific_marker_lineage")
            science_evidence.append(pre_raw.get("evidence"))
        if current_state == "scientific_terminal":
            raw_started_record = load_json(PROV / "raw_access_started.json")
            if raw_started_record.get("pre_raw_ready_sha256") != sha_file(PROV / "pre_raw_ready.json"):
                raise GateFailure("scientific_marker_lineage")
            science_evidence.append(raw_started_record.get("evidence"))
        for evidence in science_evidence:
            if not isinstance(evidence, dict):
                raise GateFailure("scientific_evidence_schema")
            evidence_compatible(baseline["evidence"], evidence)
    review = canonical_authority_review_path()
    if acquisition.get("authority_review_sha256") != sha_file(review):
        raise GateFailure("acquisition_review_hash")
    if not review_is_ship(review):
        raise GateFailure("acquisition_review_not_ship")

    expected_commands = ["clone", "sparse_init", "sparse_set", "checkout", "head", "tree",
                         "ls_tree", "object_inventory"]
    commands = acquisition.get("commands", [])
    validate_command_chain(commands, cfg)
    if [row.get("name") for row in commands] != expected_commands or any(row.get("exit_status") for row in commands):
        raise GateFailure("acquisition_command_chain")
    if any(set(row) != {"name", "argv", "exit_status", "stdout_bytes", "stdout_sha256",
                        "stderr_bytes", "stderr_sha256", "supervision_failure"} for row in commands):
        raise GateFailure("acquisition_command_schema")
    for row in commands:
        if row["supervision_failure"] is not None:
            raise GateFailure("acquisition_supervision_failure")
        if (not isinstance(row["stdout_bytes"], int) or row["stdout_bytes"] < 0
                or not isinstance(row["stderr_bytes"], int) or row["stderr_bytes"] < 0
                or not re.fullmatch(r"[0-9a-f]{64}", row["stdout_sha256"])
                or not re.fullmatch(r"[0-9a-f]{64}", row["stderr_sha256"])):
            raise GateFailure("acquisition_command_record")
    if set(acquisition.get("files", {})) != {*SOURCE_FILES.values(), LICENSE_FILE}:
        raise GateFailure("acquisition_file_set")
    if (not re.fullmatch(r"[0-9a-f]{40}", acquisition.get("tree_object_sha1", ""))
            or any(not re.fullmatch(r"[0-9a-f]{40}", row.get("git_blob_sha1", ""))
                   for row in acquisition["files"].values())):
        raise GateFailure("acquisition_git_oid")
    git_base = ["git", "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null"]
    clone = commands[0]["argv"]
    if clone[:-2] != [*git_base, "clone", "--quiet", "--filter=blob:none", "--no-checkout"] \
            or clone[-2] != REPO:
        raise GateFailure("acquisition_clone_argv")
    repo_path = clone[-1]
    exact_argv = [
        clone,
        [*git_base, "-C", repo_path, "sparse-checkout", "init", "--no-cone"],
        [*git_base, "-C", repo_path, "sparse-checkout", "set", "--no-cone",
         *SOURCE_FILES.values(), LICENSE_FILE],
        [*git_base, "-C", repo_path, "checkout", "--quiet", "--detach", COMMIT],
        [*git_base, "-C", repo_path, "rev-parse", "HEAD"],
        [*git_base, "-C", repo_path, "rev-parse", COMMIT + "^{tree}"],
        [*git_base, "-C", repo_path, "ls-tree", "-z", COMMIT, "--",
         *SOURCE_FILES.values(), LICENSE_FILE],
        [*git_base, "-C", repo_path, "cat-file", "--batch-all-objects",
         "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
    ]
    if [row["argv"] for row in commands] != exact_argv:
        raise GateFailure("acquisition_exact_argv")
    env = acquisition.get("minimal_environment", {})
    if (not isinstance(env, dict) or not all(isinstance(v, str) for v in env.values())
            or set(env) != {"PATH", "HOME", "LC_ALL", "GIT_CONFIG_NOSYSTEM", "GIT_TERMINAL_PROMPT",
                     "GIT_PROTOCOL_FROM_USER"}
            or {k: env[k] for k in env if k != "HOME"} != {
                "PATH": "/usr/bin:/bin", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0", "GIT_PROTOCOL_FROM_USER": "0"}
            or env["HOME"] != str(Path(repo_path).parent / "home")
            or acquisition.get("minimal_environment_keys") != sorted(env)):
        raise GateFailure("acquisition_environment")
    tree_listing = b"".join(
        f"100644 blob {acquisition['files'][name]['git_blob_sha1']}\t{name}\0".encode("utf-8")
        for name in sorted([*SOURCE_FILES.values(), LICENSE_FILE])
    )
    if sha_bytes(tree_listing) != acquisition.get("tree_listing_sha256"):
        raise GateFailure("acquisition_tree_listing")
    by_name = {row["name"]: row for row in commands}
    known_stdout = {
        "head": (COMMIT + "\n").encode(),
        "tree": (acquisition["tree_object_sha1"] + "\n").encode(),
        "ls_tree": tree_listing,
        "object_inventory": object_inventory,
    }
    for name, payload in known_stdout.items():
        if by_name[name]["stdout_bytes"] != len(payload) \
                or by_name[name]["stdout_sha256"] != sha_bytes(payload):
            raise GateFailure("acquisition_stdout:" + name)
    expected_blobs = sorted({row["git_blob_sha1"] for row in acquisition["files"].values()})
    if acquisition.get("local_blob_object_ids") != expected_blobs:
        raise GateFailure("acquisition_local_blobs")
    validate_history_registry(registry, cfg)
    evidence_compatible(baseline["evidence"], evidence_snapshot())
    return cfg, acquisition, registry


def load_validated_raw(acquisition: dict[str, Any]) -> dict[str, bytes]:
    counts = _RECOVERY_COUNTS.get()
    if counts is not None:
        if counts['terminal_raw_reconstruction_attempts'] != 0:
            raise GateFailure('terminal_raw_reconstruction_repeat')
        counts['terminal_raw_reconstruction_attempts'] += 1
    expected = [*SOURCE_FILES.values(), LICENSE_FILE]
    files = acquisition.get("files")
    if type(files) is not dict or set(files) != set(expected):
        raise GateFailure("outside_raw_manifest_required")
    manifests = {name:{key:item[key] for key in ["sha256","bytes","mode","nlink","pair"]}
                 for name,item in files.items()}
    jpc_runtime.verify_flat_pairs(RAW,manifests,directory_mode=0o555,file_mode=0o444)
    resources = []
    primary = None
    total = 0
    try:
        root = jpc_runtime._directory(RAW,reserve=False,mode=0o555)
        resources.append(root)
        root.validate(jpc_runtime._pair_names(expected))
        payloads = {}
        pairs = []
        for name in expected:
            receipt = jpc_runtime._expected_receipt(RAW/name,manifests[name],0o444)
            if receipt.byte_count > jpc_runtime.FILE_BYTES_LIMIT or total + receipt.byte_count > jpc_runtime.TOTAL_BYTES_LIMIT:
                raise GateFailure("raw_read_budget")
            pair = jumbo_pair.open_owned_pair(RAW/name,receipt)
            resources.append(pair);pairs.append(pair)
            payload = pair.read_bytes(max_bytes=jpc_runtime.FILE_BYTES_LIMIT)
            total += len(payload)
            blob = hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()
            if blob != files[name]["git_blob_sha1"]:
                raise GateFailure("raw_identity:"+name)
            payloads[name] = payload
        jpc_runtime._validate_all_pairs(pairs,durable=False)
        root.validate(jpc_runtime._pair_names(expected))
        return payloads
    except BaseException as exc:
        primary = exc
        raise
    finally:
        jpc_runtime._close_resources(resources,primary=primary)


def compute_science(raw_payloads: dict[str, bytes], registry: dict[str, Any],
                    cfg: dict[str, Any], *, artifacts_out: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, list[Sentence]]]:
    artifacts: dict[str, Any] = {} if artifacts_out is None else artifacts_out
    all_sentences: list[Sentence] = []
    source_manifest: dict[str, Any] = {
        "schema_version": "msae_independent_norspan_v1_source_manifest_v1",
        "source_commit": COMMIT, "partitions": {},
    }
    for partition, filename in SOURCE_FILES.items():
        try:
            text = raw_payloads[filename].decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise ScientificGateFailure("conllu_non_utf8:" + partition) from exc
        try:
            sentences, counts = parse_conllu_text(text, partition)
        except GateFailure as exc:
            raise ScientificGateFailure(str(exc)) from exc
        all_sentences.extend(sentences)
        source_manifest["partitions"][partition] = {
            **counts, "sha256": sha_bytes(raw_payloads[filename]),
        }
    artifacts["source_manifest.json"] = source_manifest

    license_report = {
        "schema_version": "msae_independent_norspan_v1_license_v1",
        "sha256": sha_bytes(raw_payloads[LICENSE_FILE]),
        "bytes": len(raw_payloads[LICENSE_FILE]),
        **license_evidence(raw_payloads[LICENSE_FILE]),
    }
    artifacts["license.json"] = license_report
    if license_report["status"] != "eligible":
        raise ScientificGateFailure("license_ineligible")
    if registry.get("blocking_alias_occurrence_count") != 0:
        raise ScientificGateFailure("source_family_ineligible")
    artifacts["candidate_pedigree.json"] = {
        "schema_version": "msae_independent_norspan_v1_candidate_pedigree_v1",
        "identifier_domain_hex": cfg["pedigree"]["domain_hex"],
        "candidate_identifier_count": len(ALIAS_SEQUENCES),
        "pathname_match_count": sum(x.get("kind") == "path" for x in registry["alias_occurrences"]),
        "content_match_count": sum(x.get("kind") != "path" for x in registry["alias_occurrences"]),
        "blocking_match_count": 0, "status": "eligible",
    }
    deduped, dedup = deduplicate(all_sentences)
    artifacts["dedup.json"] = dedup
    implicated, history = history_collisions(deduped, registry, cfg)
    artifacts["history_overlap.json"] = history
    history_filtered = [sentence for index, sentence in enumerate(deduped) if index not in implicated]
    pruned, prune = internal_prune(history_filtered)
    artifacts["internal_overlap_prune.json"] = prune
    roles, role_manifest = assign_roles(pruned)
    artifacts["role_manifest.json"] = role_manifest
    cross = cross_role_overlap(roles)
    artifacts["cross_role_overlap.json"] = cross
    if cross["status"] != "eligible":
        raise ScientificGateFailure("cross_role_overlap")
    support = support_report(roles)
    artifacts["support.json"] = support
    if support["status"] != "eligible":
        raise ScientificGateFailure("support_ineligible")
    return artifacts, roles


def cmd_prepare(args: argparse.Namespace) -> None:
    require_jpc_qualification()  # BEFORE any real state/evidence access.
    try:
        state = classify_protocol_state()
    except GateFailure:
        if (PROV / "raw_access_started.json").exists() and not (PROV / "seal.json").exists() \
                and not (PROV / "rejection.json").exists():
            raise GateFailure("raw_started_or_partial_unresolved")
        raise
    if state == "scientific_terminal":
        cmd_verify(args)
        return
    if state == "raw_started":
        raise GateFailure("raw_started_unresolved")
    if state not in {"acquisition_terminal", "scientific_entered", "raw_ready"}:
        raise GateFailure("scientific_invalid_state:" + state)
    cfg, acquisition_obj, registry = validate_control_chain()
    baseline = load_json(PROV / "baseline.json")
    if state == "acquisition_terminal":
        entry = {
            "schema_version": "msae_independent_norspan_v1_scientific_entry_v1",
            "source_acquisition_sha256": sha_file(PROV / "source_acquisition.json"),
            "history_registry_sha256": sha_file(PROV / "current_history_registry.json"),
            "config_sha256": sha_file(CONFIG_PATH), "pre_entry_evidence": evidence_snapshot(),
            "pre_entry_history_census": validate_history_registry(registry, cfg),
            "raw_accesses_before_entry": 0, "model_operations": 0, "gpu_queries": 0,
            "training_runs": 0, "status": "entered",
        }
        publish_json(PROV / "scientific_entry.json", entry)
        if classify_protocol_state() != "scientific_entered":
            raise GateFailure("scientific_entry_state")
        state = "scientific_entered"
    if state == "scientific_entered":
        publish_json(PROV / "pre_raw_ready.json", {
            "schema_version": "msae_independent_norspan_v1_pre_raw_ready_v1",
            "scientific_entry_sha256": sha_file(PROV / "scientific_entry.json"),
            "evidence": evidence_snapshot(), "history_census": validate_history_registry(registry, cfg), "status": "ready",
        })
        if classify_protocol_state() != "raw_ready":
            raise GateFailure("raw_ready_state")
        state = "raw_ready"
    if state == "raw_ready":
        publish_json(PROV / "raw_access_started.json", {
            "schema_version": "msae_independent_norspan_v1_raw_access_started_v1",
            "pre_raw_ready_sha256": sha_file(PROV / "pre_raw_ready.json"),
            "evidence": evidence_snapshot(), "history_census": validate_history_registry(registry, cfg), "status": "started",
        })
    if classify_protocol_state() != "raw_started":
        raise GateFailure("raw_started_state")
    validate_control_chain()  # Fresh complete census/row reconstruction immediately before raw open.
    # Raw custody and IO errors never become scientific negatives. Compute the
    # deterministic prefix once; only explicit scientific failures may be sealed.
    raw_payloads = load_validated_raw(acquisition_obj)
    artifacts: dict[str, Any] = {}
    failure: ScientificGateFailure | None = None
    try:
        artifacts, roles = compute_science(raw_payloads, registry, cfg, artifacts_out=artifacts)
    except ScientificGateFailure as exc:
        failure = exc
    prefix = list(artifacts)
    if prefix != list(SCIENCE_PREFIX[:len(prefix)]):
        raise GateFailure("computed_scientific_nonprefix")
    for name, obj in artifacts.items():
        publish_json(PROV / name, obj)
    if failure is not None:
        _rejection(str(failure), prefix)
        raise failure
    payloads = publish_private_roles(roles)
    custody = verify_private_payload_bytes(render_role_payloads(roles),expected_manifest=payloads)
    for role in payloads:
        if (custody[role]["sha256"] != payloads[role]["sha256"]
                or custody[role]["bytes"] != payloads[role]["bytes"]
                or custody[role]["record_count"] != payloads[role]["record_count"]):
            raise GateFailure("private_custody_reconstruction:" + role)
        payloads[role]["custody_hash_open_count"] = 1
    final_evidence = evidence_snapshot()
    validate_evidence(final_evidence)
    evidence_compatible(baseline["evidence"], final_evidence)
    ready = {
        "schema_version": "msae_independent_norspan_v1_source_ready_v1",
        "status": "ready_independently_maintained_source_accessible_history_screened",
        "source_repo": REPO, "source_commit": COMMIT, "payloads": payloads,
        "history_scope": "all_policy_accessible_current_history_before_acquisition",
        "protected_v8_v10_content_gap": True,
        "independent_replication_claimed": False, "model_pretraining_independence_claimed": False,
        "model_scoring_completed": False, "final_evidence": final_evidence,
    }
    publish_json(PROV / "source_ready.json", ready)
    gate = {
        "schema_version": "msae_independent_norspan_v1_no_training_gate_v1",
        "source_ready_sha256": sha_file(PROV / "source_ready.json"),
        "model_operations": 0, "gpu_queries": 0, "training_runs": 0,
        "model_scoring_authorized": False, "k2_or_branch_training_authorized": False,
        "stage_c_authorized": False, "status": "closed_pending_readiness_and_prescore_reviews",
    }
    publish_json(PROV / "no_training_gate.json", gate)
    seal = {
        "schema_version": "msae_independent_norspan_v1_seal_v1",
        "source_ready_sha256": sha_file(PROV / "source_ready.json"),
        "no_training_gate_sha256": sha_file(PROV / "no_training_gate.json"),
        "public_artifacts": {name: sha_file(PROV / name) for name in prefix},
        "payloads": payloads, "status": "sealed_ready_not_scored",
    }
    publish_json(PROV / "seal.json", seal)

def cmd_verify(args: argparse.Namespace) -> None:
    require_jpc_qualification()  # BEFORE any real state/evidence access.
    cfg = load_config()
    state = classify_protocol_state()
    if state not in {"acquisition_terminal", "scientific_terminal"}:
        raise GateFailure("verify_nonterminal:" + state)
    rejection = PROV / "rejection.json"
    seal_path = PROV / "seal.json"
    if state == "acquisition_terminal" and not rejection.exists() and not seal_path.exists():
        cfg,acquisition,registry = validate_control_chain()
        manifests = {name:{key:item[key] for key in ['sha256','bytes','mode','nlink','pair']}
                     for name,item in acquisition['files'].items()}
        jpc_runtime.verify_flat_pairs(RAW,manifests,directory_mode=0o555,file_mode=0o444)
        validate_history_registry(registry,cfg)
        return {'status':'verified_acquisition_not_scored','scientific_raw_accesses':0}
    if rejection.exists() == seal_path.exists():
        raise GateFailure("terminal_cardinality")
    if rejection.exists():
        cfg, baseline, _authority, registry = validate_authority_chain()
        obj = canonical_control(rejection)
        status = obj.get("status")
        common = {"schema_version", "status", "failure_code", "evidence", "model_operations", "gpu_queries", "training_runs", "next_action"}
        require_literals(obj, {"schema_version": "msae_independent_norspan_v1_rejection_jpc_v1" if status == "rejected_during_acquisition" else "msae_independent_norspan_v1_rejection_v1",
                              "model_operations": 0, "gpu_queries": 0, "training_runs": 0,
                              "next_action": "new_reviewed_protocol_only"}, "rejection")
        if not isinstance(obj.get("failure_code"), str) or not obj["failure_code"]:
            raise GateFailure("rejection_failure_code")
        if status == "rejected_during_acquisition":
            if state != "acquisition_terminal" or set(obj) != common | {
                "commands", "scratch", "acquisition_entry_sha256", "network_started_sha256", "authority_sha256"}:
                raise GateFailure("acquisition_rejection_schema")
            require_literals(obj, {
                "acquisition_entry_sha256": sha_file(PROV / "acquisition_entry.json"),
                "network_started_sha256": sha_file(PROV / "network_started.json"),
                "authority_sha256": sha_file(PROV / "authority.json"),
            }, "acquisition_rejection_lineage")
            validate_command_chain(obj["commands"], cfg, rejection=True)
            last = obj["commands"][-1]
            expected_code = ("source_subprocess_" + last["supervision_failure"]
                             if last["supervision_failure"] is not None else "source_acquisition_" + last["name"])
            if obj["failure_code"] != expected_code:
                raise GateFailure("acquisition_rejection_failure_observation")
            validate_scratch_record(obj["scratch"])
        elif status == "rejected_after_scientific_entry":
            if state != "scientific_terminal" or set(obj) != common | {
                "published_scientific_prefix", "public_artifacts", "raw_access_started_sha256", "source_acquisition_sha256"}:
                raise GateFailure("scientific_rejection_schema")
            cfg, acquisition, registry = validate_control_chain()
            require_literals(obj, {"raw_access_started_sha256": sha_file(PROV / "raw_access_started.json"),
                                  "source_acquisition_sha256": sha_file(PROV / "source_acquisition.json")}, "rejection_lineage")
            expected_artifacts: dict[str, Any] = {}
            observed_failure: str | None = None
            try:
                compute_science(load_validated_raw(acquisition), registry, cfg, artifacts_out=expected_artifacts)
            except ScientificGateFailure as exc:
                observed_failure = str(exc)
            actual_prefix = [name for name in SCIENCE_PREFIX if name in protocol_inventory()["public"]]
            if (observed_failure is None or obj["failure_code"] != observed_failure
                    or obj["published_scientific_prefix"] != list(expected_artifacts)
                    or actual_prefix != list(expected_artifacts)):
                raise GateFailure("rejection_first_failure_or_prefix")
            for name, expected in expected_artifacts.items():
                if canonical_bytes(canonical_control(PROV / name)) != canonical_bytes(expected):
                    raise GateFailure("rejection_scientific_drift:" + name)
            if obj["public_artifacts"] != {name: sha_file(PROV / name) for name in expected_artifacts}:
                raise GateFailure("rejection_artifact_binding")
        else:
            raise GateFailure("rejection_schema")
        validate_evidence(obj["evidence"])
        evidence_compatible(baseline["evidence"], obj["evidence"])
        validate_history_registry(registry, cfg)
        current = evidence_snapshot()
        validate_evidence(current); evidence_compatible(baseline["evidence"], current)
        return {"status":"verified_rejection","failure_code":obj["failure_code"]}
    if state != "scientific_terminal":
        raise GateFailure("success_not_scientific_terminal")
    cfg, acquisition, registry = validate_control_chain()
    raw_payloads = load_validated_raw(acquisition)
    expected_artifacts, roles = compute_science(raw_payloads, registry, cfg)
    for name in SCIENCE_PREFIX:
        expected = expected_artifacts[name]
        if read_bytes_nofollow(PROV / name) != canonical_file_bytes(expected):
            raise GateFailure("scientific_artifact_drift:" + name)
    seal = canonical_control(seal_path, "schema_version source_ready_sha256 no_training_gate_sha256 public_artifacts payloads status".split())
    ready = canonical_control(PROV / "source_ready.json", "schema_version status source_repo source_commit payloads history_scope protected_v8_v10_content_gap independent_replication_claimed model_pretraining_independence_claimed model_scoring_completed final_evidence".split())
    gate = canonical_control(PROV / "no_training_gate.json", "schema_version source_ready_sha256 model_operations gpu_queries training_runs model_scoring_authorized k2_or_branch_training_authorized stage_c_authorized status".split())
    require_literals(seal, {"schema_version": "msae_independent_norspan_v1_seal_v1", "status": "sealed_ready_not_scored"}, "seal")
    require_literals(ready, {
        "schema_version": "msae_independent_norspan_v1_source_ready_v1",
        "status": "ready_independently_maintained_source_accessible_history_screened",
        "source_repo": REPO, "source_commit": COMMIT,
        "history_scope": "all_policy_accessible_current_history_before_acquisition",
        "protected_v8_v10_content_gap": True, "independent_replication_claimed": False,
        "model_pretraining_independence_claimed": False, "model_scoring_completed": False,
    }, "source_ready")
    require_literals(gate, {
        "schema_version": "msae_independent_norspan_v1_no_training_gate_v1",
        "source_ready_sha256": sha_file(PROV / "source_ready.json"),
        "model_operations": 0, "gpu_queries": 0, "training_runs": 0,
        "model_scoring_authorized": False, "k2_or_branch_training_authorized": False, "stage_c_authorized": False,
        "status": "closed_pending_readiness_and_prescore_reviews",
    }, "no_training_gate")
    if not isinstance(ready["payloads"], dict) or set(ready["payloads"]) != {"discovery", "calibration", "C1", "C2"}:
        raise GateFailure("ready_payload_role_set")
    validate_evidence(ready["final_evidence"])
    if seal["source_ready_sha256"] != sha_file(PROV / "source_ready.json") or seal["no_training_gate_sha256"] != sha_file(PROV / "no_training_gate.json"):
        raise GateFailure("seal_lineage")
    if any(gate[name] for name in ("model_operations", "gpu_queries", "training_runs")):
        raise GateFailure("operation_count")
    if any(gate[name] for name in ("model_scoring_authorized", "k2_or_branch_training_authorized",
                                   "stage_c_authorized")):
        raise GateFailure("premature_authorization")
    if seal.get("public_artifacts") != {name: sha_file(PROV / name) for name in SCIENCE_PREFIX}:
        raise GateFailure("seal_public_artifacts")
    if seal.get("payloads") != ready.get("payloads"):
        raise GateFailure("seal_payload_manifest")
    expected_payloads = render_role_payloads(roles)
    custody = verify_private_payload_bytes(expected_payloads,expected_manifest=ready["payloads"])
    for role, item in ready["payloads"].items():
        expected = expected_payloads[role]
        if canonical_bytes(item) != canonical_bytes({
            "sha256": sha_bytes(expected), "record_count": len(roles[role]), "bytes": len(expected),
            "mode": 0o600, "nlink": 2, "pair": item["pair"], "custody_hash_open_count": 1, "scientific_open_count": 0,
        }):
            raise GateFailure("payload_manifest:" + role)
        if custody[role]["sha256"] != item["sha256"] or custody[role]["bytes"] != item["bytes"]:
            raise GateFailure("payload_bytes:" + role)
    baseline = load_json(PROV / "baseline.json")
    evidence_compatible(baseline["evidence"], ready["final_evidence"])
    evidence_compatible(baseline["evidence"], evidence_snapshot())
    return {"status":"verified_ready_not_scored","payload_roles":sorted(ready["payloads"])}



def cmd_recover(args: argparse.Namespace):
    require_jpc_qualification()
    import msae_norspan_jpc_controller as controller
    return controller.from_arguments(args).execute("recover")


def main() -> None:
    import msae_norspan_jpc_controller as controller
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["build-history","build-authority","prepare","verify","recover"]:
        controller.add_arguments(sub.add_parser(name),genesis=name=="build-history")
    args = parser.parse_args()
    active = controller.from_arguments(args,genesis=args.command=="build-history")
    result = active.execute(args.command,args)
    print(json.dumps({"result":result,"outside_catalog":str(active.catalog.path),
                      "catalog_sha256":active.catalog.sha256,"source_work_authorized":False},sort_keys=True))


if __name__ == "__main__":
    main()
