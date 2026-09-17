"""NORSPAN-1 publication/retention foundation; whole launch is NOT qualified.

No source acquisition, scientific parser, history census, model or process launch
is present here. Expected receipts come from the caller's outside approved trust
root, never from observing visible files. All created and foreign evidence stays
in place on both success and failure. Client observations are conditional, not server/backup guarantees. The reviewed
no-admin client contract does not satisfy unverified hard scientific containment.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

import msae_jumbo_pair_commit as j


class RuntimeBlocked(RuntimeError):
    """Operational/qualification failure, never a scientific negative result."""


AMENDMENT_PATH = "configs/msae_independent_norspan_v1/jpc_publication_retention_v1.json"
AMENDMENT_SHA256 = "02bbc4a2d127c795dac56722254c33d5cdd093a281c05823957cc70452bff37b"
ORIGINAL_SHA256 = "645fc34db2a770113c6c8ef531e9317f3209e4d6f1d31c18b55daecad6151420"
SCIENTIFIC_FIELDS = (
    "source", "license", "pedigree", "role", "support", "overlap", "payload",
    "gates", "containment", "decision_rules", "history", "capability",
    "authorizations", "acquisition_limits", "runtime", "state_order",
)
ROLES = ("discovery", "calibration", "C1", "C2")
CONTROL_NAMES = frozenset({
    "current_history_registry.json", "baseline.json", "authority.json",
    "acquisition_entry.json", "pre_network_ready.json", "network_started.json",
    "source_acquisition.json", "scientific_entry.json", "pre_raw_ready.json",
    "raw_access_started.json", "source_manifest.json", "license.json",
    "candidate_pedigree.json", "dedup.json", "history_overlap.json",
    "internal_overlap_prune.json", "role_manifest.json", "cross_role_overlap.json",
    "support.json", "source_ready.json", "no_training_gate.json", "seal.json",
    "rejection.json",
})
FILE_BYTES_LIMIT = 8 * 1024**3
TOTAL_BYTES_LIMIT = 64 * 1024**3
ENTRY_LIMIT = 65536


def require_whole_qualification() -> None:
    """Fail closed BEFORE real state inspection until remaining integration lands.

    Deliberately no report-name/first-line fallback. Controller/authentication
    code does not establish owner trust enrollment, exact whole approval, full
    matrix qualification or required hard containment. Remain unconditionally
    blocked before any real state observation or source operation.
    """
    raise RuntimeBlocked("jpc_whole_qualification_pending")


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha_literal(value, label: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise RuntimeBlocked("invalid_sha256:" + label)


def _json(raw: bytes):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeBlocked("duplicate_json_key:" + key)
            result[key] = value
        return result
    def nonfinite(value):
        raise RuntimeBlocked("nonfinite_json:" + value)
    try:
        return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=unique,
                          parse_constant=nonfinite)
    except (ValueError, UnicodeError) as exc:
        raise RuntimeBlocked("invalid_json") from exc


def read_ordinary_file(path: Path, *, mode: int = 0o644, max_bytes: int = 4 * 1024**2) -> bytes:
    """Ordinary code/config/review files remain exact nlink1, NOT paired."""
    j._names(path)
    parent = j._open_parent_fd(path)
    fd = None
    primary = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) != mode or before.st_size > max_bytes):
            raise RuntimeBlocked("ordinary_file_custody")
        chunks = []
        count = 0
        while block := os.read(fd, min(1024**2, max_bytes - count + 1)):
            count += len(block)
            if count > max_bytes:
                raise RuntimeBlocked("ordinary_file_too_large")
            chunks.append(block)
        if (count != before.st_size
                or j._fingerprint(os.fstat(fd)) != j._fingerprint(before)
                or j._fingerprint(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) != j._fingerprint(before)):
            raise RuntimeBlocked("ordinary_file_drift")
        j._validate_parent_fd(parent)
        return b"".join(chunks)
    except BaseException as exc:
        primary = exc
        raise
    finally:
        j._finish(parent, fd, primary)


def scientific_projection(original: dict) -> dict:
    if type(original) is not dict or not set(SCIENTIFIC_FIELDS) <= set(original):
        raise RuntimeBlocked("scientific_projection_schema")
    return {field: original[field] for field in SCIENTIFIC_FIELDS}


def validate_projection(original: dict, amendment: dict) -> None:
    if (type(amendment) is not dict or "scientific_projection" not in amendment
            or canonical_bytes(scientific_projection(original)) != canonical_bytes(amendment["scientific_projection"])):
        raise RuntimeBlocked("scientific_projection_drift")


def load_amendment(root: Path) -> dict:
    raw = read_ordinary_file(root / AMENDMENT_PATH)
    if hashlib.sha256(raw).hexdigest() != AMENDMENT_SHA256:
        raise RuntimeBlocked("amendment_exact_bytes_drift")
    cfg = _json(raw)
    original_raw = read_ordinary_file(root / "configs/msae_independent_norspan_v1/protocol.json")
    if hashlib.sha256(original_raw).hexdigest() != ORIGINAL_SHA256:
        raise RuntimeBlocked("original_protocol_exact_bytes_drift")
    validate_projection(_json(original_raw), cfg)
    return cfg



CLIENT_CONTRACT_PATH = "configs/msae_independent_norspan_v1/jumbo_client_storage_v1.json"
CLIENT_CONTRACT_SHA256 = "2922d5c9a9908e5a188f0b7a095e4ec2c4b6cc086df3222a0316baa2c45f377f"


def load_client_contract(root: Path) -> dict:
    """Separately named no-admin proposal, NEVER old-contract reinterpretation."""
    raw = read_ordinary_file(root / CLIENT_CONTRACT_PATH)
    if hashlib.sha256(raw).hexdigest() != CLIENT_CONTRACT_SHA256:
        raise RuntimeBlocked("client_contract_exact_bytes_drift")
    cfg = _json(raw)
    original = read_ordinary_file(root / "configs/msae_independent_norspan_v1/protocol.json")
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA256:
        raise RuntimeBlocked("original_protocol_exact_bytes_drift")
    validate_projection(_json(original), cfg)
    contract = read_ordinary_file(root / cfg["contract_path"], mode=0o700)
    if hashlib.sha256(contract).hexdigest() != cfg["contract_sha256"]:
        raise RuntimeBlocked("client_contract_document_drift")
    return cfg

def _close_resources(resources, *, primary: BaseException | None) -> None:
    """Finish every resource despite errors; preserve first operation/close fault."""
    first = primary
    for resource in reversed(resources):
        try:
            resource.close(primary=first)
        except BaseException as exc:
            if first is None:
                first = exc
            else:
                first.add_note("jpc_secondary_close:" + type(exc).__name__ + ":" + str(exc))
    if primary is None and first is not None:
        raise first



def bounded_names(fd: int, cap: int, *, reason: str = "directory_cardinality") -> set[str]:
    """Incremental cap+1 rejection; close the iterator on every exit."""
    names = set()
    iterator = os.scandir(fd)
    primary = None
    try:
        for seen, entry in enumerate(iterator, 1):
            if seen > cap:
                raise RuntimeBlocked(reason)
            names.add(entry.name)
        return names
    except BaseException as exc:
        primary = exc
        raise
    finally:
        try:
            iterator.close()
        except BaseException as exc:
            if primary is None:
                raise
            primary.add_note("scandir_secondary_close:" + type(exc).__name__ + ":" + str(exc))


def _current_fd_count() -> int:
    """Conservative finite client count, NOT a kernel-wide hard FD limit."""
    fd = os.open("/proc/self/fd", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    primary = None
    try:
        return len(bounded_names(fd,4096,reason="scratch_fd_admission"))
    except BaseException as exc:
        primary = exc
        raise
    finally:
        j._close_fds([fd],primary=primary)

def admit_observation_fds(path: Path | None = None, *, additional: int = 0) -> None:
    """Scoped current-process admission; NOT kernel/concurrent-writer quota.

    len(parts) covers root, all absolute parents and leaf. Eight conservative
    slots cover monitoring/scandir and constructor/subprocess transients.
    Repeat for every retained constructor, counting already-held originals.
    """
    if type(additional) is not int or not 0 <= additional <= 4096:
        raise RuntimeBlocked('observation_fd_reserve_schema')
    reserve = additional + 8
    if path is not None:
        if '.msae_keys' in path.parts:
            raise RuntimeBlocked('history_credential_namespace_prohibited')
        j._names(path)
        reserve += len(path.parts)
    if _current_fd_count() + reserve > 4096:
        raise RuntimeBlocked('observation_fd_admission')


class _Directory:
    def __init__(self, path: Path, parent, fd: int, identity):
        self.path, self.parent, self.fd, self.identity = path, parent, fd, identity
        self.closed = False

    def validate(self, names=None, *, durable: bool = False) -> None:
        if self.closed:
            raise RuntimeBlocked("directory_handle_closed")
        j._validate_parent_fd(self.parent)
        if (j._directory_identity(os.fstat(self.fd)) != self.identity
                or j._directory_identity(os.stat(self.path.name, dir_fd=self.parent, follow_symlinks=False)) != self.identity):
            raise RuntimeBlocked("directory_identity_drift")
        if names is not None and bounded_names(self.fd, len(names)) != set(names):
            raise RuntimeBlocked("directory_cardinality")
        if durable:
            os.fsync(self.fd)
            os.fsync(self.parent)
            self.validate(names)

    def make_readonly(self) -> None:
        self.validate()
        if self.identity[3] != 0o700:
            raise RuntimeBlocked("directory_mode_transition")
        os.fchmod(self.fd, 0o555)
        self.identity = (*self.identity[:3], 0o555)
        self.validate()

    def close(self, *, primary: BaseException | None = None) -> None:
        if not self.closed:
            self.closed = True
            j._finish(self.parent, self.fd, primary)

    def __enter__(self):
        try:
            self.validate()
            return self
        except BaseException as exc:
            self.close(primary=exc)
            raise

    def __exit__(self, exc_type, exc, traceback):
        self.close(primary=exc)


def _directory(path: Path, *, reserve: bool, mode: int) -> _Directory:
    j._names(path)
    parent = j._open_parent_fd(path)
    fd = None
    try:
        if reserve:
            os.mkdir(path.name, mode, dir_fd=parent)  # exclusive, no reuse
            os.fsync(parent)
        named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        identity = j._directory_identity(named)
        if identity[3] != mode:
            raise RuntimeBlocked("directory_mode")
        fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        directory = _Directory(path, parent, fd, identity)
        directory.validate(durable=reserve)
        return directory
    except BaseException as exc:
        j._finish(parent, fd, exc)
        raise


def _component(name) -> None:
    if (type(name) is not str or not name or name.startswith(".")
            or "/" in name or "\0" in name):
        raise RuntimeBlocked("invalid_logical_pair_name")


def _pair_names(names) -> set[str]:
    result = set()
    for name in names:
        _component(name)
        result.update({name, "." + name + ".stage"})
    return result


def _manifest(pair: j.OwnedPair) -> dict:
    receipt = pair.receipt
    return {"sha256": receipt.sha256, "bytes": receipt.byte_count,
            "mode": receipt.mode, "nlink": 2, "pair": j.receipt_record(receipt)}


def _expected_receipt(path: Path, item: dict, mode: int) -> j.PairReceipt:
    if type(item) is not dict or set(item) != {"sha256", "bytes", "mode", "nlink", "pair"}:
        raise RuntimeBlocked("pair_manifest_schema")
    receipt = j.receipt_from_record(path, item["pair"])
    expected = {"sha256": receipt.sha256, "bytes": receipt.byte_count,
                "mode": mode, "nlink": 2, "pair": j.receipt_record(receipt)}
    if receipt.mode != mode or canonical_bytes(item) != canonical_bytes(expected):
        raise RuntimeBlocked("pair_manifest_literals")
    return receipt


def _validate_all_pairs(pairs, *, durable: bool) -> None:
    """Digest every original FD, then check ALL earlier verified fingerprints.

    Capturing BEFORE each digest is essential: a fingerprint harvested after a
    digest could bless intervening foreign bytes. The last digest/fsync must not
    mutate an earlier object unnoticed. Final checks do not rebase expectations.
    This is bounded custody, not exclusion of arbitrary future same-UID writes.
    """
    verified = []
    for pair in pairs:
        before = j._fingerprint(os.fstat(pair.fd))
        pair.validate(durable=durable)
        verified.append((pair, before))
    # Additional all-original byte phase AFTER every earlier validation.
    for pair, _before in verified:
        j._expected_byte_fence(pair.parent, pair.fd, pair.receipt)
    for pair, before in verified:
        j._validate_parent_fd(pair.parent)
        j._check_stat(os.fstat(pair.fd), pair.receipt, 2)
        if j._fingerprint(os.fstat(pair.fd)) != before:
            raise RuntimeBlocked("aggregate_verified_fd_drift")
        for name in (pair.receipt.stage_name, pair.receipt.final_name):
            if j._fingerprint(os.stat(name, dir_fd=pair.parent, follow_symlinks=False)) != before:
                raise RuntimeBlocked("aggregate_verified_alias_drift")
        j._absent(pair.parent, "." + pair.receipt.final_name + ".building")
        j._validate_parent_fd(pair.parent)


def publish_flat_pairs(path: Path, files: dict, *, directory_mode: int, file_mode: int) -> dict:
    if (type(files) is not dict or not files or type(directory_mode) is not int
            or directory_mode not in {0o700, 0o555} or type(file_mode) is not int
            or file_mode not in {0o444, 0o600, 0o644}):
        raise RuntimeBlocked("flat_publication_schema")
    names = _pair_names(files)
    if len(files) > ENTRY_LIMIT // 2:
        raise RuntimeBlocked("flat_entry_budget")
    if any(type(payload) is not bytes for payload in files.values()):
        raise RuntimeBlocked("flat_payload_schema")
    if any(len(payload) > FILE_BYTES_LIMIT for payload in files.values()) or sum(map(len, files.values())) > TOTAL_BYTES_LIMIT:
        raise RuntimeBlocked("flat_byte_budget")
    resources = []
    primary = None
    try:
        root = _directory(path, reserve=True, mode=0o700)
        resources.append(root)
        pairs = {}
        for name, payload in files.items():
            root.validate()
            pairs[name] = j.create_owned_pair(path / name, payload, mode=file_mode)
            resources.append(pairs[name])
        root.validate(names)
        if directory_mode == 0o555:
            root.make_readonly()
            for pair in pairs.values():
                pair.accept_readonly_parent()
        root.validate(names, durable=True)
        _validate_all_pairs(pairs.values(), durable=True)
        root.validate(names)
        return {name: _manifest(pair) for name, pair in pairs.items()}
    except BaseException as exc:
        primary = exc
        raise
    finally:
        _close_resources(resources, primary=primary)


def verify_flat_pairs(path: Path, manifest: dict, *, directory_mode: int, file_mode: int,
                      durable: bool = False) -> dict:
    if type(manifest) is not dict or not manifest or type(durable) is not bool:
        raise RuntimeBlocked("flat_verification_schema")
    names = _pair_names(manifest)
    if len(manifest) > ENTRY_LIMIT // 2:
        raise RuntimeBlocked("flat_entry_budget")
    receipts = {name: _expected_receipt(path / name, item, file_mode) for name, item in manifest.items()}
    if sum(receipt.byte_count for receipt in receipts.values()) > TOTAL_BYTES_LIMIT:
        raise RuntimeBlocked("flat_byte_budget")
    resources = []
    primary = None
    try:
        root = _directory(path, reserve=False, mode=directory_mode)
        resources.append(root)
        root.validate(names)
        pairs = []
        for name, receipt in receipts.items():
            pair = j.open_owned_pair(path / name, receipt)
            resources.append(pair)
            pairs.append(pair)
        root.validate(names, durable=durable)
        _validate_all_pairs(pairs, durable=durable)
        root.validate(names)
        return manifest
    except BaseException as exc:
        primary = exc
        raise
    finally:
        _close_resources(resources, primary=primary)


def _role_aggregate(path: Path, values: dict, *, reserve: bool, durable: bool) -> dict:
    if type(values) is not dict or set(values) != set(ROLES) or type(durable) is not bool:
        raise RuntimeBlocked("role_aggregate_schema")
    if reserve and any(type(payload) is not bytes for payload in values.values()):
        raise RuntimeBlocked("role_payload_schema")
    resources = []
    primary = None
    try:
        root = _directory(path, reserve=reserve, mode=0o700)
        resources.append(root)
        directories, pairs = {}, {}
        for role in ROLES:
            root.validate()
            directory = _directory(path / role.lower(), reserve=reserve, mode=0o700)
            directories[role] = directory
            resources.append(directory)
            final = directory.path / "payload.jsonl"
            if reserve:
                pair = j.create_owned_pair(final, values[role], mode=0o600)
            else:
                receipt = _expected_receipt(final, values[role], 0o600)
                pair = j.open_owned_pair(final, receipt)
            pairs[role] = pair
            resources.append(pair)
        expected_root = {role.lower() for role in ROLES}
        expected_role = {"payload.jsonl", ".payload.jsonl.stage"}
        root.validate(expected_root, durable=durable)
        identities = {(pair.receipt.device, pair.receipt.inode) for pair in pairs.values()}
        if len(identities) != 4:
            raise RuntimeBlocked("cross_role_inode")
        for role in ROLES:
            directories[role].validate(expected_role, durable=durable)
        _validate_all_pairs(pairs.values(), durable=durable)
        for directory in directories.values():
            directory.validate(expected_role)
        root.validate(expected_root)
        return {role: _manifest(pair) for role, pair in pairs.items()}
    except BaseException as exc:
        primary = exc
        raise
    finally:
        _close_resources(resources, primary=primary)


def publish_role_pairs(path: Path, payloads: dict) -> dict:
    return _role_aggregate(path, payloads, reserve=True, durable=True)


def verify_role_pairs(path: Path, manifest: dict, *, durable: bool = False) -> dict:
    return _role_aggregate(path, manifest, reserve=False, durable=durable)


class ScratchLease(_Directory):
    """Pinned explicit-Jumbo scratch; closing NEVER deletes or moves evidence."""
    def __init__(self, directory: _Directory, binding: dict):
        super().__init__(directory.path, directory.parent, directory.fd, directory.identity)
        self.binding = binding
        directory.closed = True  # transfer ownership only after construction

    def validate_pristine(self) -> None:
        self.validate({"home"}, durable=True)
        with _directory(self.path / "home", reserve=False, mode=0o700) as home:
            home.validate(set(), durable=True)
        self.validate({"home"})

    def snapshot(self, *, durable: bool = False, file_bytes: int = FILE_BYTES_LIMIT,
                 total_bytes: int = TOTAL_BYTES_LIMIT, entries: int = ENTRY_LIMIT) -> dict:
        if (type(durable) is not bool or any(type(v) is not int or v < 1 for v in (file_bytes, total_bytes, entries))
                or file_bytes > FILE_BYTES_LIMIT or total_bytes > TOTAL_BYTES_LIMIT or entries > ENTRY_LIMIT):
            raise RuntimeBlocked("scratch_budget_schema")
        self.validate()
        root_names = bounded_names(self.fd, 2, reason="scratch_root_cardinality")
        if not {"home"} <= root_names <= {"home", "repo"}:
            raise RuntimeBlocked("scratch_root_cardinality")
        counts = {"entries": 0, "total_bytes": 0}
        # Root is preowned; every descendant stays open through the final fence.
        records = []
        owned = []
        primary = None
        # Includes current unrelated/ancestry FDs and temporary enumeration FDs;
        # conservative rejection leaves headroom for each later scandir.
        baseline_fd_count = _current_fd_count()
        if baseline_fd_count + 2 > 4096:
            raise RuntimeBlocked("scratch_fd_admission")
        def admit(fd, parent, name, expected, depth):
            is_directory = stat.S_ISDIR(expected.st_mode)
            record = {"fd": fd, "parent": parent, "name": name,
                      "fingerprint": j._fingerprint(expected), "directory": is_directory,
                      "names": None}
            records.append(record)
            if not is_directory:
                return
            cap = min(1024 - len(records), entries - counts["entries"])
            names = bounded_names(fd, cap, reason="scratch_object_admission")
            record["names"] = names
            if parent == self.fd and name == "home" and (names or stat.S_IMODE(expected.st_mode) != 0o700):
                raise RuntimeBlocked("scratch_home_not_pristine")
            for child_name in sorted(names):
                if len(records) >= 1024:
                    raise RuntimeBlocked("scratch_object_admission")
                if depth >= 64:
                    raise RuntimeBlocked("scratch_depth_admission")
                if baseline_fd_count + len(owned) + 3 > 4096:
                    raise RuntimeBlocked("scratch_fd_admission")
                counts["entries"] += 1
                if counts["entries"] > entries:
                    raise RuntimeBlocked("scratch_entry_budget")
                named = os.stat(child_name, dir_fd=fd, follow_symlinks=False)
                flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                if stat.S_ISDIR(named.st_mode):
                    flags |= os.O_DIRECTORY
                elif stat.S_ISREG(named.st_mode) and named.st_nlink == 1:
                    if named.st_size > file_bytes:
                        raise RuntimeBlocked("scratch_file_budget")
                    counts["total_bytes"] += named.st_size
                    if counts["total_bytes"] > total_bytes:
                        raise RuntimeBlocked("scratch_total_budget")
                else:
                    raise RuntimeBlocked("scratch_special_or_alias:" + child_name)
                child = os.open(child_name, flags, dir_fd=fd)
                owned.append(child)
                if j._fingerprint(os.fstat(child)) != j._fingerprint(named):
                    raise RuntimeBlocked("scratch_child_identity_drift")
                admit(child, fd, child_name, named, depth + 1)
        try:
            admit(self.fd, self.parent, self.path.name, os.fstat(self.fd), 0)
            if durable:
                for record in reversed(records):
                    os.fsync(record["fd"])
            self.validate(root_names, durable=durable)
            # Preserve BOTH retained named-alias test boundaries, no rebasing.
            for _pass in range(2):
                for record in records:
                    if j._fingerprint(os.stat(record["name"], dir_fd=record["parent"], follow_symlinks=False)) != record["fingerprint"]:
                        raise RuntimeBlocked("scratch_final_object_drift")
                    if record["directory"] and bounded_names(record["fd"], len(record["names"])) != record["names"]:
                        raise RuntimeBlocked("scratch_final_names_drift")
            self.validate(root_names)
            # Materially different final fence: ALL original held objects,
            # including earlier directories, after the last named observation.
            for record in records:
                if record["directory"] and bounded_names(record["fd"], len(record["names"])) != record["names"]:
                    raise RuntimeBlocked("scratch_original_directory_names_drift")
                if j._fingerprint(os.fstat(record["fd"])) != record["fingerprint"]:
                    raise RuntimeBlocked("scratch_original_fd_drift")
            return {"schema_version": "norspan_jpc_retained_scratch_v1", "binding": dict(self.binding),
                    "retained": True, "cleanup_attempts": 0, "current_fsync_completed": durable,
                    **counts, "budget_monitor_is_hard_quota": False,
                    "observation_contract": "controlled_writer_multi_observation_not_atomic",
                    "retained_object_count": len(records), "server_backup_guarantees": "UNKNOWN"}
        except BaseException as exc:
            primary = exc
            raise
        finally:
            j._close_fds(reversed(owned), primary=primary)



def _validate_scratch_binding(binding: dict) -> Path:
    keys = {"schema_version", "path", "device", "inode", "mode", "authority_sha256",
            "entry_lineage_sha256", "cleanup_attempts"}
    if type(binding) is not dict or set(binding) != keys:
        raise RuntimeBlocked("scratch_binding_schema")
    if (binding["schema_version"] != "norspan_jpc_scratch_binding_v1"
            or type(binding["path"]) is not str or type(binding["mode"]) is not int or binding["mode"] != 0o700
            or type(binding["cleanup_attempts"]) is not int or binding["cleanup_attempts"] != 0
            or any(type(binding[key]) is not int or binding[key] < 0 for key in ("device", "inode"))
            or binding["inode"] == 0):
        raise RuntimeBlocked("scratch_binding_literals")
    _sha_literal(binding["authority_sha256"], "authority")
    _sha_literal(binding["entry_lineage_sha256"], "entry_lineage")
    path = Path(binding["path"])
    j._names(path)
    if str(path) != binding["path"]:
        raise RuntimeBlocked("scratch_path_not_canonical")
    return path


def reserve_scratch(path: Path, *, authority_sha256: str, entry_lineage_sha256: str) -> ScratchLease:
    _sha_literal(authority_sha256, "authority")
    _sha_literal(entry_lineage_sha256, "entry_lineage")
    directory = _directory(path, reserve=True, mode=0o700)
    try:
        with _directory(path / "home", reserve=True, mode=0o700) as home:
            home.validate(set(), durable=True)
        directory.validate({"home"}, durable=True)
        binding = {"schema_version": "norspan_jpc_scratch_binding_v1", "path": str(path),
                   "device": directory.identity[0], "inode": directory.identity[1], "mode": 0o700,
                   "authority_sha256": authority_sha256, "entry_lineage_sha256": entry_lineage_sha256,
                   "cleanup_attempts": 0}
        return ScratchLease(directory, binding)
    except BaseException as exc:
        directory.close(primary=exc)
        raise


def reopen_scratch(binding: dict) -> ScratchLease:
    """Caller must first authenticate the exact PRE-START containing control."""
    path = _validate_scratch_binding(binding)
    directory = _directory(path, reserve=False, mode=0o700)
    try:
        if directory.identity[:2] != (binding["device"], binding["inode"]):
            raise RuntimeBlocked("scratch_bound_inode_drift")
        return ScratchLease(directory, dict(binding))
    except BaseException as exc:
        directory.close(primary=exc)
        raise


def recover_current_custody(root: Path, expected_catalog: dict, *, expected_catalog_sha256: str,
                           lineage_sha256: str) -> dict:
    """Fresh explicit opaque reconstruction, with NO source-work authorization.

    The supplied catalog digest must originate outside the paired namespace from
    a trusted independent approval. Never discover expectations from the files.
    This foundation validates custody, not full control schemas/scientific replay;
    later production recovery MUST perform those before permitting first access.
    """
    _sha_literal(expected_catalog_sha256, "catalog")
    _sha_literal(lineage_sha256, "lineage")
    if (type(expected_catalog) is not dict
            or set(expected_catalog) != {"schema_version", "lineage_sha256", "controls"}
            or expected_catalog["schema_version"] != "norspan_jpc_custody_catalog_v1"
            or expected_catalog["lineage_sha256"] != lineage_sha256
            or hashlib.sha256(canonical_bytes(expected_catalog)).hexdigest() != expected_catalog_sha256):
        raise RuntimeBlocked("untrusted_recovery_catalog")
    controls = expected_catalog["controls"]
    if type(controls) is not dict or not controls or not set(controls) <= CONTROL_NAMES:
        raise RuntimeBlocked("recovery_controls_schema")
    receipts = {name: j.receipt_from_record(root / name, record) for name, record in controls.items()}
    if any(receipt.mode != 0o644 for receipt in receipts.values()):
        raise RuntimeBlocked("recovery_control_mode")
    resources = []
    primary = None
    try:
        directory = _directory(root, reserve=False, mode=stat.S_IMODE(root.lstat().st_mode))
        resources.append(directory)
        names = bounded_names(directory.fd, len(CONTROL_NAMES) * 2,
                              reason="recovery_directory_entry_limit")
        network_started = bool({"network_started.json", ".network_started.json.stage"} & names)
        raw_started = bool({"raw_access_started.json", ".raw_access_started.json.stage"} & names)
        terminal = ("rejection.json" in controls or "seal.json" in controls
                    or ("source_acquisition.json" in controls and not raw_started))
        if (network_started or raw_started) and not terminal:
            raise RuntimeBlocked("started_without_terminal_no_retry")
        directory.validate(_pair_names(controls))
        pairs = []
        for name, receipt in receipts.items():
            pair = j.open_owned_pair(root / name, receipt)
            pairs.append(pair)
            resources.append(pair)
        directory.validate(_pair_names(controls), durable=True)
        _validate_all_pairs(pairs, durable=True)
        directory.validate(_pair_names(controls))
        return {"status": "terminal_current_custody" if terminal else "prestart_current_custody",
                "catalog_sha256": expected_catalog_sha256, "source_operations": 0,
                "model_operations": 0, "source_work_authorized": False,
                "historical_producer_success_inferred": False}
    except BaseException as exc:
        primary = exc
        raise
    finally:
        _close_resources(resources, primary=primary)
