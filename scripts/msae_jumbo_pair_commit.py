"""JPC-1 custody primitives; production launch requires separate whole approval.

Both the exclusive staging name and no-replace final hardlink remain permanently.
Namespace visibility alone is not approval: callers must additionally bind a
successful receipt to their independently reviewed containing authority/manifest.
Retained handles permit aggregate publishers to hold original descriptors through
their final checks. This module grants no source/model/scoring capability. All
failures retain every created or foreign object.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path
import re
import stat


class PairFailure(RuntimeError):
    """Source-free pair custody failure, never scientific negative evidence."""


class _PinnedParent(int):
    def __new__(cls, descriptors, links):
        obj = int.__new__(cls, descriptors[-1])
        obj.descriptors = tuple(descriptors)
        obj.links = tuple(links)
        obj.root_identity = _directory_identity(os.fstat(descriptors[0]))
        return obj


def _directory_identity(s: os.stat_result) -> tuple[int, ...]:
    if not stat.S_ISDIR(s.st_mode):
        raise PairFailure("pair_parent_not_directory")
    return (s.st_dev, s.st_ino, stat.S_IFMT(s.st_mode), stat.S_IMODE(s.st_mode))


def _close_fds(descriptors, *, primary: BaseException | None = None) -> None:
    """Close each owned FD ONCE, even after Linux close errors/interrupts.

    On Linux a close error other than EBADF releases the descriptor: never retry
    close, which could close an unrelated reused FD. Preserve a primary operation
    error, attaching cleanup failures; otherwise propagate the first close error.
    """
    errors = []
    for fd in descriptors:
        try:
            os.close(fd)
        except BaseException as exc:
            errors.append(exc)
    if not errors:
        return
    if primary is not None:
        for exc in errors:
            primary.add_note("pair_secondary_close:" + type(exc).__name__ + ":" + str(exc))
        return
    for exc in errors[1:]:
        errors[0].add_note("pair_secondary_close:" + type(exc).__name__ + ":" + str(exc))
    raise errors[0]


def _validate_parent_fd(parent: _PinnedParent) -> None:
    if (_directory_identity(os.fstat(parent.descriptors[0])) != parent.root_identity
            or _directory_identity(os.stat("/", follow_symlinks=False)) != parent.root_identity):
        raise PairFailure("pair_parent_chain_root_drift")
    for fd, name, child, expected in parent.links:
        try:
            named = os.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise PairFailure("pair_parent_chain_drift:" + name) from exc
        if (_directory_identity(named) != expected
                or _directory_identity(os.fstat(child)) != expected):
            raise PairFailure("pair_parent_chain_drift:" + name)


def _open_parent_fd(path: Path) -> _PinnedParent:
    # Does not create ancestors; an approved destination must already exist.
    descriptors = [os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)]
    links = []
    try:
        for name in path.parts[1:-1]:
            parent = descriptors[-1]
            before = os.stat(name, dir_fd=parent, follow_symlinks=False)
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            descriptors.append(child)
            expected = _directory_identity(before)
            if _directory_identity(os.fstat(child)) != expected:
                raise PairFailure("pair_parent_chain_drift:" + name)
            links.append((parent, name, child, expected))
        pinned = _PinnedParent(descriptors, links)
        _validate_parent_fd(pinned)
        return pinned
    except BaseException as exc:
        _close_fds(reversed(descriptors), primary=exc)
        raise


def _finish(parent: _PinnedParent, owned: int | None, primary: BaseException | None) -> None:
    descriptors = ([] if owned is None else [owned]) + list(reversed(parent.descriptors))
    _close_fds(descriptors, primary=primary)


@dataclass(frozen=True)
class PairReceipt:
    device: int
    inode: int
    mode: int
    byte_count: int
    sha256: str
    stage_name: str
    final_name: str


def _names(path: Path) -> tuple[str, str]:
    if not isinstance(path, Path) or not path.is_absolute():
        raise PairFailure("pair_requires_absolute_jumbo_path")
    if ".." in path.parts or path.parts[:2] != ("/", "jumbo"):
        raise PairFailure("pair_requires_absolute_jumbo_path")
    final = path.name
    if not final or final in {".", ".."} or "\0" in final or "/" in final:
        raise PairFailure("invalid_pair_component")
    return "." + final + ".stage", final


def _validate_receipt(receipt: PairReceipt, stage: str, final: str) -> None:
    if type(receipt) is not PairReceipt:
        raise PairFailure("pair_receipt_schema")
    for field in ("device", "inode", "mode", "byte_count"):
        value = getattr(receipt, field)
        if type(value) is not int or value < 0:
            raise PairFailure("pair_receipt_schema:" + field)
    if (receipt.inode == 0 or receipt.byte_count > 8 * 1024**3 or receipt.mode not in {0o444, 0o600, 0o644}
            or type(receipt.sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", receipt.sha256) is None
            or type(receipt.stage_name) is not str or type(receipt.final_name) is not str
            or receipt.stage_name != stage or receipt.final_name != final):
        raise PairFailure("pair_receipt_schema")


def _absent(parent: int, name: str) -> None:
    try:
        os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise PairFailure("pair_obstruction:" + name)


def _fingerprint(s: os.stat_result) -> tuple[int, ...]:
    return (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size,
            s.st_mtime_ns, s.st_ctime_ns)


def _check_stat(s: os.stat_result, receipt: PairReceipt, nlink: int) -> None:
    if (not stat.S_ISREG(s.st_mode)
            or (s.st_dev, s.st_ino, stat.S_IMODE(s.st_mode), s.st_size, s.st_nlink)
            != (receipt.device, receipt.inode, receipt.mode, receipt.byte_count, nlink)):
        raise PairFailure("pair_original_inode_or_metadata")



def _digest_expected(owned: int, receipt: PairReceipt) -> None:
    """Bounded observed ORIGINAL-FD bytes, never a timestamp-only claim."""
    digest = hashlib.sha256()
    offset = 0
    while True:
        chunk = os.pread(owned, min(1024 * 1024, receipt.byte_count - offset + 1), offset)
        if not chunk:
            break
        offset += len(chunk)
        if offset > receipt.byte_count:
            raise PairFailure("pair_byte_count_drift")
        digest.update(chunk)
    if offset != receipt.byte_count or digest.hexdigest() != receipt.sha256:
        raise PairFailure("pair_actual_bytes")


def _expected_byte_fence(parent, owned: int, receipt: PairReceipt) -> None:
    """Additional finite byte/alias observation, NOT an atomic snapshot.

    NFS may retain identical timestamps after a rapid same-length rewrite.
    Expected bytes must be observed again after the existing validation phase.
    Arbitrary writes during/after this last observation are not excluded; callers
    require the independently reviewed controlled-writer assumption.
    """
    _validate_parent_fd(parent)
    before = os.fstat(owned)
    _check_stat(before, receipt, 2)
    _digest_expected(owned, receipt)
    if _fingerprint(os.fstat(owned)) != _fingerprint(before):
        raise PairFailure("pair_final_byte_fd_drift")
    for name in (receipt.stage_name, receipt.final_name):
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _check_stat(named, receipt, 2)
        if _fingerprint(named) != _fingerprint(before):
            raise PairFailure("pair_final_byte_alias_drift")
    _absent(parent, "." + receipt.final_name + ".building")
    _validate_parent_fd(parent)

def _check(parent: int, owned: int, receipt: PairReceipt, *, complete: bool) -> None:
    """Validate owned-FD bytes, exact named aliases and read-time metadata."""
    _validate_parent_fd(parent)
    _absent(parent, "." + receipt.final_name + ".building")
    nlink = 2 if complete else 1
    before = os.fstat(owned)
    _check_stat(before, receipt, nlink)
    names = (receipt.stage_name, receipt.final_name) if complete else (receipt.stage_name,)
    for name in names:
        try:
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise PairFailure("pair_missing_name:" + name) from exc
        _check_stat(named, receipt, nlink)
        if _fingerprint(named) != _fingerprint(before):
            raise PairFailure("pair_named_fingerprint_drift")
    if not complete:
        _absent(parent, receipt.final_name)
    _digest_expected(owned, receipt)
    if _fingerprint(os.fstat(owned)) != _fingerprint(before):
        raise PairFailure("pair_read_time_drift")
    for name in names:
        try:
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise PairFailure("pair_missing_name:" + name) from exc
        if _fingerprint(named) != _fingerprint(before):
            raise PairFailure("pair_postread_named_drift")
    if not complete:
        _absent(parent, receipt.final_name)
    _absent(parent, "." + receipt.final_name + ".building")
    _validate_parent_fd(parent)


def _insert_final(parent: int, stage: str, final: str) -> None:
    # Path substitution here can expose an invalid final. Postchecks must reject
    # it, and no containing approval may be published from the failed invocation.
    os.link(stage, final, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)


class OwnedPair:
    """Original writer/reader and full ancestry retained until explicit close.

    Validation is explicit: context exit closes resources but does not silently
    certify a containing manifest or recover a failed invocation. Close attempts
    happen once, including when Linux reports an error after releasing the FD.
    """

    def __init__(self, parent: _PinnedParent, fd: int, receipt: PairReceipt):
        self.parent, self.fd, self.receipt = parent, fd, receipt
        self.closed = False

    def _require_open(self) -> None:
        if self.closed:
            raise PairFailure("pair_handle_closed")

    def validate(self, *, durable: bool = False) -> PairReceipt:
        self._require_open()
        if type(durable) is not bool:
            raise PairFailure("pair_durable_schema")
        _check(self.parent, self.fd, self.receipt, complete=True)
        if durable:
            os.fsync(self.fd)
            os.fsync(self.parent)
            _check(self.parent, self.fd, self.receipt, complete=True)
        _expected_byte_fence(self.parent, self.fd, self.receipt)
        return self.receipt

    def accept_readonly_parent(self) -> None:
        """Accept ONLY the caller's explicit immediate-parent 0700 -> 0555.

        Raw aggregates must finish chmod while writers remain owned. All ancestors
        except this one exact inode retain their original identity and mode. No
        file, directory substitution or arbitrary permission change is accepted.
        """
        self._require_open()
        parent = self.parent
        owner, name, child, old = parent.links[-1]
        expected = (*old[:3], 0o555)
        if (old[3] != 0o700
                or _directory_identity(os.fstat(child)) != expected
                or _directory_identity(os.stat(name, dir_fd=owner, follow_symlinks=False)) != expected):
            raise PairFailure("pair_readonly_parent_transition")
        # Update only after all other links have been validated; restore the
        # old binding if any ancestor or owned-file check fails.
        original_links = parent.links
        parent.links = (*original_links[:-1], (owner, name, child, expected))
        try:
            self.validate()
        except BaseException:
            parent.links = original_links
            raise

    def read_bytes(self, *, max_bytes: int) -> bytes:
        """Bounded consumer read against an externally supplied expectation.

        Callers still need containing authority and role capability. Reading a
        matching pair alone is never a scientific-readiness decision.
        """
        self._require_open()
        if type(max_bytes) is not int or max_bytes < 0:
            raise PairFailure("pair_read_limit_schema")
        if self.receipt.byte_count > max_bytes:
            raise PairFailure("pair_file_too_large")
        return self._read_expected_prefix(self.receipt.byte_count)

    def read_prefix(self, *, limit: int) -> bytes:
        """Keep only a finite prefix while hashing the complete expected bytes.

        Custody still requires full streaming integrity observations before,
        during and after copying. This bounds retained output, not total I/O or
        arbitrary concurrent-writer isolation. Never substitute limit for the
        expected whole-file byte budget or harvest a new hash from visible data.
        """
        self._require_open()
        if type(limit) is not int or not 1 <= limit <= 8 * 1024**3:
            raise PairFailure("pair_prefix_limit_schema")
        return self._read_expected_prefix(min(limit, self.receipt.byte_count))

    def _read_expected_prefix(self, output_bytes: int) -> bytes:
        """Original-FD streaming whole digest; retain at most output_bytes."""
        self.validate()
        before = _fingerprint(os.fstat(self.fd))
        chunks = []
        offset = 0
        digest = hashlib.sha256()
        while offset < self.receipt.byte_count:
            block = os.pread(self.fd, min(1024 * 1024, self.receipt.byte_count - offset), offset)
            if not block:
                raise PairFailure("pair_read_short")
            if offset < output_bytes:
                chunks.append(block[:output_bytes - offset])
            digest.update(block)
            offset += len(block)
        if (digest.hexdigest() != self.receipt.sha256
                or _fingerprint(os.fstat(self.fd)) != before):
            raise PairFailure("pair_read_time_drift")
        self.validate()
        return b"".join(chunks)

    def close(self, *, primary: BaseException | None = None) -> None:
        if not self.closed:
            self.closed = True  # before the first close; errors must not retry
            _finish(self.parent, self.fd, primary)

    def __enter__(self) -> OwnedPair:
        self._require_open()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close(primary=exc)


def receipt_record(receipt: PairReceipt) -> dict:
    if type(receipt) is not PairReceipt:
        raise PairFailure("pair_receipt_schema")
    _validate_receipt(receipt, receipt.stage_name, receipt.final_name)
    return asdict(receipt)


def receipt_from_record(path: Path, record: dict) -> PairReceipt:
    stage, final = _names(path)
    if type(record) is not dict or set(record) != set(PairReceipt.__dataclass_fields__):
        raise PairFailure("pair_receipt_record_schema")
    receipt = PairReceipt(**record)
    _validate_receipt(receipt, stage, final)
    return receipt


def create_owned_pair(path: Path, payload: bytes, *, mode: int) -> OwnedPair:
    """Create once; transfer descriptors only after all single-pair checks.

    On failure close all descriptors once, preserving the primary exception and
    every created/foreign object. On success the caller MUST close the handle.
    """
    stage, final = _names(path)
    if type(payload) is not bytes or type(mode) is not int or mode not in {0o444, 0o600, 0o644}:
        raise PairFailure("pair_payload_or_mode_schema")
    parent = _open_parent_fd(path)
    owned = None
    try:
        for name in (stage, final, "." + final + ".building"):
            _absent(parent, name)
        try:
            owned = os.open(stage, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                            0o600, dir_fd=parent)
        except FileExistsError as exc:
            raise PairFailure("pair_stage_already_reserved") from exc
        original = os.fstat(owned)
        if not stat.S_ISREG(original.st_mode) or original.st_nlink != 1:
            raise PairFailure("pair_initial_inode")
        offset = 0
        while offset < len(payload):
            count = os.write(owned, payload[offset:])
            if type(count) is not int or count <= 0 or count > len(payload) - offset:
                raise PairFailure("pair_write_count")
            offset += count
        os.fchmod(owned, mode)
        receipt = PairReceipt(original.st_dev, original.st_ino, mode, len(payload),
                              hashlib.sha256(payload).hexdigest(), stage, final)
        os.fsync(owned)
        os.fsync(parent)
        _check(parent, owned, receipt, complete=False)
        _insert_final(parent, stage, final)
        _check(parent, owned, receipt, complete=True)
        os.fsync(owned)
        os.fsync(parent)
        _check(parent, owned, receipt, complete=True)
        _expected_byte_fence(parent, owned, receipt)
        return OwnedPair(parent, owned, receipt)
    except BaseException as exc:
        _finish(parent, owned, exc)
        raise


def open_owned_pair(path: Path, receipt: PairReceipt, *, durable: bool = False) -> OwnedPair:
    """Opaque current custody check against an EXTERNALLY approved receipt.

    Current fsync success is not proof that a past producer returned successfully,
    and this function grants no semantic consumption or state-recovery permission.
    """
    stage, final = _names(path)
    _validate_receipt(receipt, stage, final)
    if type(durable) is not bool:
        raise PairFailure("pair_durable_schema")
    parent = _open_parent_fd(path)
    owned = None
    try:
        try:
            owned = os.open(final, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except (FileNotFoundError, IsADirectoryError) as exc:
            raise PairFailure("pair_final_unavailable") from exc
        _check(parent, owned, receipt, complete=True)
        if durable:
            os.fsync(owned)
            os.fsync(parent)
            _check(parent, owned, receipt, complete=True)
        _expected_byte_fence(parent, owned, receipt)
        return OwnedPair(parent, owned, receipt)
    except BaseException as exc:
        _finish(parent, owned, exc)
        raise


def create_pair(path: Path, payload: bytes, *, mode: int) -> PairReceipt:
    """Single-object convenience wrapper, not sufficient for aggregate custody."""
    with create_owned_pair(path, payload, mode=mode) as pair:
        return pair.receipt


def verify_pair(path: Path, receipt: PairReceipt, *, durable: bool = False) -> PairReceipt:
    with open_owned_pair(path, receipt, durable=durable) as pair:
        return pair.receipt
