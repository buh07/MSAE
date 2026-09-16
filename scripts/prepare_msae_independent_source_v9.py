#!/usr/bin/env python3
"""Source-readiness builder for MSAE v9; standard-library and model-free."""
from __future__ import annotations

import argparse
import ast
import codecs
import collections
import dataclasses
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
import gzip
import io
import tarfile
import zipfile
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "c434778d9511be5c35a6a11531f0107a960fb5d6"
REPO = "https://github.com/UniversalDependencies/UD_Swedish-Talbanken.git"
RAW = ROOT / "data/msae_independent_source_v9/raw" / COMMIT
PRIVATE = ROOT / "data/msae_independent_source_v9/private"
PROV = ROOT / "reports/provenance/msae_independent_source_v9"
QUARANTINES = {
    "data/atlas_v1/private/final.jsonl",
    "data/atlas_v1/private/final.records.jsonl",
    "data/atlas_v1/private/final.units.jsonl",
}
SOURCE_FILES = {
    "train": "sv_talbanken-ud-train.conllu",
    "dev": "sv_talbanken-ud-dev.conllu",
    "test": "sv_talbanken-ud-test.conllu",
}
UPOS = frozenset("ADJ ADP ADV AUX CCONJ DET INTJ NOUN NUM PART PRON PROPN PUNCT SCONJ SYM VERB X".split())
DEPREL = frozenset("acl advcl advmod amod appos aux case cc ccomp clf compound conj cop csubj dep det discourse dislocated expl fixed flat goeswith iobj list mark nmod nsubj nummod obj obl orphan parataxis punct reparandum root vocative xcomp".split())
NUMBER = frozenset("Sing Plur Dual Trial Pauc Grpa Grpl Inv Ptan".split())
TASKS = ("absolute_bucket", "relative_quartile", "token_identity", "lemma_identity",
         "capitalization", "word_length", "punctuation", "sentence_boundary",
         "head_signed_distance", "dependency_depth", "upos_coarse", "deprel_coarse", "number")
REQUIRED = {"absolute_bucket", "relative_quartile", "capitalization", "word_length",
            "punctuation", "sentence_boundary", "head_signed_distance", "upos_coarse"}
OPTIONAL = {"dependency_depth", "deprel_coarse", "number", "token_identity", "lemma_identity"}
GENERATED_PREFIXES = (".git/", ".venv-atlas/", ".pytest_cache/", ".generated/")
V9_PREFIX = "data/msae_independent_source_v9/"
V8_DATA_PREFIX = "data/msae_independent_source_v8/"
CARRYOVER_PATH = "reports/provenance/msae_independent_source_v9/v8_carryover_authority.json"
CARRYOVER_SHA256 = "00d7cdca4e9893ef1f4e36b6104caf21991ce1ca92e9897d3c5a72d497212f47"
V8_CONTROL_PATHS = {
    "docs/plan-msae-independent-source-v8.md",
    "reports/adversarial/msae_independent_source_v8_plan_review.md",
    "scripts/prepare_msae_independent_source_v8.py",
    "scripts/acquire_msae_independent_source_v8.py",
    "tests/test_prepare_msae_independent_source_v8.py",
    "configs/msae_independent_source_v8/acquisition.json",
    "reports/verification/msae_independent_source_v8_source_free_checks.log",
    "reports/adversarial/msae_independent_source_v8_preacquisition_implementation_review.md",
    "reports/adversarial/msae_independent_source_v8_preacquisition_authority_review.md",
    "reports/adversarial/msae_independent_source_v8_terminal_failure_review.md",
    "reports/provenance/msae_independent_source_v8/preacquisition_alias_screen.json",
    "reports/provenance/msae_independent_source_v8/historical_source_registry.json",
    "reports/provenance/msae_independent_source_v8/baseline_inventory.json",
    "reports/provenance/msae_independent_source_v8/preacquisition_authority_manifest.json",
    "reports/provenance/msae_independent_source_v8/source_acquisition_entry.json",
    "reports/provenance/msae_independent_source_v8/source_acquisition.json",
    "reports/provenance/msae_independent_source_v8/rejection.json",
}
V9_AUTHORITY = {
    "docs/plan-msae-independent-source-v9.md",
    "reports/adversarial/msae_independent_source_v9_plan_review.md",
    CARRYOVER_PATH,
    "reports/provenance/msae_independent_source_v9/preacquisition_alias_screen.json",
    "reports/provenance/msae_independent_source_v9/historical_source_registry.json",
    "reports/provenance/msae_independent_source_v9/preacquisition_authority_manifest.json",
    "reports/provenance/msae_independent_source_v9/baseline_inventory.json",
    "scripts/prepare_msae_independent_source_v9.py",
    "scripts/acquire_msae_independent_source_v9.py",
    "tests/test_prepare_msae_independent_source_v9.py",
    "configs/msae_independent_source_v9/acquisition.json",
    "reports/verification/msae_independent_source_v9_source_free_checks.log",
    "reports/adversarial/msae_independent_source_v9_preacquisition_implementation_review.md",
    "reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md",
}
V9_FROZEN_AUTHORITY_SHA256 = {
    "docs/plan-msae-independent-source-v9.md":
        "0607886af9561d8418fd7a153322e6b59cd47404f33174c49b07bec5284cd57e",
    "reports/adversarial/msae_independent_source_v9_plan_review.md":
        "5e471cde50c9b4cda8e8f4ad8aca178e235d8a8b9d981a78d9e5b588f96aaee7",
    CARRYOVER_PATH: CARRYOVER_SHA256,
    "reports/provenance/msae_independent_source_v9/historical_source_registry.json":
        "3166d09141374506d7d200fa8d630a66e4a790f5a3f2e81778ed522d4a327863",
    "reports/provenance/msae_independent_source_v9/preacquisition_alias_screen.json":
        "cdda84035279b78698f98c760c5ce12d5276b9b2afbc8e4218133d8207dccafd",
}

SCIENTIFIC_ARTIFACT_NAMES = (
    "document_group_census.json", "source_manifest.json", "license.json", "source_family.json",
    "candidate_pedigree.json", "dedup.json", "cross_role_overlap.json", "history_manifest.json",
    "history_overlap.json", "support.json", "role_manifest.json", "split_manifest.json",
    "post_process_snapshot.json", "no_training_gate.json", "seal.json",
)
BINARY_SUFFIXES = {".pyc", ".so", ".a", ".pt", ".npy", ".npz", ".pkl", ".png", ".pdf",
                   ".parquet", ".feather", ".orc", ".fits", ".gz", ".zip", ".tar", ".lock"}
LEX = re.compile(r"[^\W_]+", re.UNICODE)
ALIAS_TOKEN_SEQUENCES = (("ud", "swedish", "talbanken"), ("swedish", "talbanken"), ("sv", "talbanken"),
                         ("https", "github", "com", "universaldependencies", "ud", "swedish", "talbanken", "git"),
                         (COMMIT,))
FORBIDDEN_PROCESS_TOKENS=("torchrun","train_msae","msae_train","branch_training","run_branch_train",
                          "deepspeed","accelerate launch","nvidia-smi","cuda_visible_devices")
RAW_FILE_OPEN_COUNT = 0
RAW_ACCESS_AUTHORIZED = False
DYNAMIC_PREFLIGHT_STARTED = False
ENTRY_PUBLICATION_STARTED = False
# Keep the custody boundary anchored to the real project namespace even when
# unit tests monkeypatch ``RAW`` to exercise individual parsers on fixtures.
# Tests that exercise the boundary itself can monkeypatch this constant.
REAL_V9_RAW = RAW

class GateFailure(RuntimeError):
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
    sent_id: str
    tokens: tuple[Token, ...]
    source_index: int
    group_id: str | None = None


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_file_bytes(value: Any) -> bytes:
    return canonical_bytes(value) + b"\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def open_repo_file(path: Path) -> int:
    global RAW_FILE_OPEN_COUNT
    is_v9_raw=path.is_relative_to(REAL_V9_RAW)
    if is_v9_raw and not RAW_ACCESS_AUTHORIZED:
        raise GateFailure("v9_raw_open_before_scientific_entry")
    try:rel=path.relative_to(ROOT)
    except ValueError:
        fd=os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
        opened=os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):os.close(fd);raise GateFailure("nonregular_open")
        if is_v9_raw:RAW_FILE_OPEN_COUNT+=1
        return fd
    root_stat=ROOT.lstat()
    if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):raise GateFailure("unsafe_repository_root")
    dfd=os.open(ROOT,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0))
    try:
        opened_root=os.fstat(dfd)
        if (opened_root.st_dev,opened_root.st_ino)!=(root_stat.st_dev,root_stat.st_ino):raise GateFailure("repository_root_identity_drift")
        for component in rel.parent.parts:
            next_fd=os.open(component,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0),dir_fd=dfd)
            os.close(dfd);dfd=next_fd
        fd=os.open(rel.name,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0),dir_fd=dfd)
    finally:
        os.close(dfd)
    opened=os.fstat(fd)
    if not stat.S_ISREG(opened.st_mode):os.close(fd);raise GateFailure("nonregular_open")
    if is_v9_raw:RAW_FILE_OPEN_COUNT+=1
    return fd


def open_repo_dir(path: Path) -> int:
    try:
        rel=path.relative_to(ROOT)
    except ValueError:
        return os.open(path,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0))
    root_stat=ROOT.lstat()
    if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):raise GateFailure("unsafe_repository_root")
    dfd=os.open(ROOT,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0))
    try:
        opened_root=os.fstat(dfd)
        if (opened_root.st_dev,opened_root.st_ino)!=(root_stat.st_dev,root_stat.st_ino):raise GateFailure("repository_root_identity_drift")
        for component in rel.parts:
            next_fd=os.open(component,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0),dir_fd=dfd)
            os.close(dfd);dfd=next_fd
        return dfd
    except BaseException:
        os.close(dfd);raise


def directory_snapshot_nofollow(path: Path) -> tuple[os.stat_result, list[str]]:
    """List a directory through its pinned inode and reject path exchange."""
    before=path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise GateFailure("path_identity_changed")
    fd=open_repo_dir(path)
    try:
        opened=os.fstat(fd)
        if _directory_fingerprint(before)!=_directory_fingerprint(opened):
            raise GateFailure("path_identity_changed")
        names=sorted(os.listdir(fd))
        after=os.fstat(fd);current=path.lstat()
        if (_directory_fingerprint(opened)!=_directory_fingerprint(after)
                or _directory_fingerprint(opened)!=_directory_fingerprint(current)):
            raise GateFailure("path_identity_changed")
        return opened,names
    except OSError as error:
        raise GateFailure("path_identity_changed") from error
    finally:
        os.close(fd)


def lstat_child_nofollow(directory: Path, name: str) -> os.stat_result:
    dfd=open_repo_dir(directory)
    try:
        return os.stat(name,dir_fd=dfd,follow_symlinks=False)
    finally:
        os.close(dfd)


def read_bytes_nofollow(path: Path) -> bytes:
    fd=open_repo_file(path)
    try:
        before=os.fstat(fd);chunks=[]
        while True:
            block=os.read(fd,1024*1024)
            if not block:break
            chunks.append(block)
        after=os.fstat(fd)
        if (before.st_dev,before.st_ino,before.st_mode,before.st_size,before.st_mtime_ns)!=(
                after.st_dev,after.st_ino,after.st_mode,after.st_size,after.st_mtime_ns):
            raise GateFailure("file_mutated_while_reading")
        return b"".join(chunks)
    finally:os.close(fd)


def read_text_nofollow(path: Path) -> str:
    return read_bytes_nofollow(path).decode("utf-8")


def sha_file(path: Path) -> str:
    return sha_bytes(read_bytes_nofollow(path))


def regular_state_nofollow(path: Path, *, mode: int | None = None,
                           nlink: int | None = None) -> os.stat_result:
    """Open every component without following links and validate the opened inode."""
    fd = open_repo_file(path)
    try:
        opened = os.fstat(fd)
        if (mode is not None and stat.S_IMODE(opened.st_mode) != mode) or (
                nlink is not None and opened.st_nlink != nlink):
            raise GateFailure("regular_file_custody_drift")
        return opened
    finally:
        os.close(fd)


def present_path(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def sha_regular_nofollow(path: Path) -> str:
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode):
        raise GateFailure("not_regular_for_hash")
    digest=sha_file(path);after=path.lstat()
    if (after.st_dev,after.st_ino,after.st_mode,after.st_size,after.st_mtime_ns)!=(
            before.st_dev,before.st_ino,before.st_mode,before.st_size,before.st_mtime_ns):
        raise GateFailure("path_identity_changed")
    return digest


def lstat_state(path: Path, *, hash_regular_final: bool = False,
                valid_payload_final: bool = False) -> dict[str, Any]:
    rel=path.relative_to(ROOT).as_posix()
    try:s=path.lstat()
    except FileNotFoundError:return {"path":rel,"state":"absent"}
    kind=("regular" if stat.S_ISREG(s.st_mode) else "directory" if stat.S_ISDIR(s.st_mode)
          else "symlink" if stat.S_ISLNK(s.st_mode) else "other")
    item={"path":rel,"state":"present","type":kind,
          "mode":stat.S_IMODE(s.st_mode),"nlink":s.st_nlink,"size":s.st_size}
    if hash_regular_final and kind=="regular":item["sha256"]=sha_regular_nofollow(path)
    if valid_payload_final and kind=="regular" and stat.S_IMODE(s.st_mode)==0o600 and s.st_nlink==1:
        item["sha256"]=sha_regular_nofollow(path)
    return item


def scientific_artifact_inventory() -> dict[str, Any]:
    entries=[]
    for name in ("scientific_preparation_entry.json", "preflight_rejection.json", "rejection.json",
                 *SCIENTIFIC_ARTIFACT_NAMES):
        final=PROV/name;temporary=final.with_name("."+final.name+".building")
        entries.append(lstat_state(final,hash_regular_final=True))
        entries.append(lstat_state(temporary))
    return {"schema_version":"msae_independent_source_v9_scientific_artifact_inventory_v1",
            "entries":entries}


def payload_state() -> list[dict[str, Any]]:
    final=PRIVATE/"blind_payload.jsonl";temporary=PRIVATE/".blind_payload.jsonl.building"
    return [lstat_state(final,valid_payload_final=True),lstat_state(temporary)]


def git_blob_sha1(path: Path) -> str:
    payload=read_bytes_nofollow(path);h=hashlib.sha1(usedforsecurity=False)
    h.update(f"blob {len(payload)}\0".encode("ascii"));h.update(payload)
    return h.hexdigest()


def cleanup_created_temp(dfd: int, name: str, identity: tuple[int, int]) -> None:
    current=os.stat(name,dir_fd=dfd,follow_symlinks=False)
    if (current.st_dev,current.st_ino)!=identity:raise GateFailure("temporary_identity_changed")
    os.unlink(name,dir_fd=dfd);os.fsync(dfd)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_file_bytes(value)
    parent=path.parent
    try:path.relative_to(ROOT)
    except ValueError:dfd=os.open(parent,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0))
    else:dfd=open_repo_dir(parent)
    parent_stat=os.fstat(dfd)
    tmp_name="."+path.name+".building"
    try:
        for candidate,code in ((tmp_name,"abandoned_public_temporary"),(path.name,"public_artifact_exists")):
            try:os.stat(candidate,dir_fd=dfd,follow_symlinks=False)
            except FileNotFoundError:continue
            raise GateFailure(code)
        fd=os.open(tmp_name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o644,dir_fd=dfd)
        created=os.fstat(fd);identity=(created.st_dev,created.st_ino)
        try:
            os.fchmod(fd,0o644);position=0
            while position<len(data):
                written=os.write(fd,data[position:])
                if written<=0:raise OSError("short public write")
                position+=written
            os.fsync(fd)
        except BaseException:
            os.close(fd);cleanup_created_temp(dfd,tmp_name,identity);raise
        else:os.close(fd)
        try:os.link(tmp_name,path.name,src_dir_fd=dfd,dst_dir_fd=dfd,follow_symlinks=False)
        except BaseException:
            cleanup_created_temp(dfd,tmp_name,identity);raise
        cleanup_created_temp(dfd,tmp_name,identity)
        final=os.stat(path.name,dir_fd=dfd,follow_symlinks=False);after=os.fstat(dfd)
        if (not stat.S_ISREG(final.st_mode) or stat.S_IMODE(final.st_mode)!=0o644 or final.st_nlink!=1
                or (after.st_dev,after.st_ino)!=(parent_stat.st_dev,parent_stat.st_ino)):
            raise GateFailure("public_artifact_verification")
        os.fsync(dfd)
    finally:
        os.close(dfd)


def strict_json(path: Path) -> Any:
    payload=read_bytes_nofollow(path);value=strict_json_loads(payload.decode("utf-8"))
    # These two pre-plan artifacts have exact reviewed SHA-256 values and an indented canonical
    # presentation; every builder-published v9 final uses canonical_file_bytes.
    if path.name not in {"historical_source_registry.json","preacquisition_alias_screen.json"} and payload!=canonical_file_bytes(value):
        raise GateFailure("noncanonical_public_json")
    return value


def strict_terminal_json(path: Path) -> Any:
    """Read one canonical terminal final through a custody-bound descriptor."""
    try:
        fd=open_repo_file(path)
    except (GateFailure,OSError) as error:
        raise GateFailure("terminal_final_custody") from error
    try:
        before=os.fstat(fd)
        if stat.S_IMODE(before.st_mode)!=0o644 or before.st_nlink!=1:
            raise GateFailure("terminal_final_custody")
        chunks=[]
        while True:
            block=os.read(fd,1024*1024)
            if not block:break
            chunks.append(block)
        after=os.fstat(fd)
        try:current=path.lstat()
        except OSError as error:raise GateFailure("terminal_final_custody") from error
        fingerprint=lambda value:(value.st_dev,value.st_ino,value.st_mode,value.st_nlink,
                                  value.st_size,value.st_mtime_ns,value.st_ctime_ns)
        if fingerprint(before)!=fingerprint(after) or fingerprint(before)!=fingerprint(current):
            raise GateFailure("terminal_final_custody")
        payload=b"".join(chunks)
    finally:
        os.close(fd)
    value=strict_json_loads(payload.decode("utf-8"))
    if payload!=canonical_file_bytes(value):raise GateFailure("noncanonical_public_json")
    return value


def strict_json_loads(value: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, item in items:
            if key in out:
                raise GateFailure("duplicate_json_member")
            out[key] = item
        return out
    return json.loads(value, object_pairs_hook=pairs,
                      parse_constant=lambda _x: (_ for _ in ()).throw(GateFailure("nonfinite_json_constant")))


def exact_keys(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise GateFailure(code)
    return value


def verify_process_snapshot_schema(value: Any, code: str) -> None:
    exact_keys(value, {"schema_version", "observation_scope", "forbidden_tokens", "process_count",
                       "entries", "forbidden_identity_count", "status"}, code)
    entries = value["entries"]
    if not isinstance(entries,list) or any(not isinstance(item,dict) for item in entries):raise GateFailure(code)
    if (value["schema_version"] != "msae_independent_source_v9_process_snapshot_v1"
            or value["observation_scope"] != "point_in_time_proc_snapshot"
            or value["forbidden_tokens"]!=list(FORBIDDEN_PROCESS_TOKENS)
            or value["process_count"] != len(entries)
            or not isinstance(value["process_count"],int) or isinstance(value["process_count"],bool)
            or not isinstance(value["forbidden_identity_count"],int) or isinstance(value["forbidden_identity_count"],bool)
            or value["forbidden_identity_count"]<0
            or value["status"] != ("eligible" if value["forbidden_identity_count"]==0 else "ineligible")
            or any(set(item) != {"pid", "start_ticks", "executable_basename", "command_sha256", "forbidden_codes"}
                   or not isinstance(item["pid"],int) or isinstance(item["pid"],bool) or item["pid"]<0
                   or not isinstance(item["start_ticks"],str) or not isinstance(item["executable_basename"],str)
                   or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("command_sha256", "")))
                   or not isinstance(item["forbidden_codes"],list)
                   or item["forbidden_codes"]!=sorted(set(item["forbidden_codes"]))
                   or any(token not in FORBIDDEN_PROCESS_TOKENS for token in item["forbidden_codes"])
                   for item in entries)
            or value["forbidden_identity_count"] != sum(bool(item["forbidden_codes"]) for item in entries)):
        raise GateFailure(code)


def validate_acquisition_config(path: Path) -> dict[str, Any]:
    value = strict_json(path)
    expected_files = [SOURCE_FILES[role] for role in ("train", "dev", "test")] + ["LICENSE.txt"]
    expected_clone = ["git", "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null",
                      "clone", "--quiet", "--filter=blob:none", "--no-checkout", REPO, "${CLONE_DIR}"]
    expected_checkout = ["git", "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null",
                         "-c", "core.sparseCheckout=true", "-C", "${CLONE_DIR}", "checkout", "--quiet", "--detach", COMMIT]
    expected_environment = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
                            "HOME": "${EMPTY_HOME}", "PATH": "/usr/bin:/bin"}
    expected_proxy_names = ["ALL_PROXY", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
                            "all_proxy", "https_proxy", "http_proxy", "no_proxy"]
    expected_head=["git","-C","${CLONE_DIR}","rev-parse","HEAD"]
    expected_tree=["git","-C","${CLONE_DIR}","rev-parse","${SOURCE_COMMIT}^{tree}"]
    expected_ls_tree=["git","-C","${CLONE_DIR}","ls-tree","-z","${SOURCE_COMMIT}","--",*expected_files]
    expected_hash_object=["git","-C","${CLONE_DIR}","hash-object","--no-filters","${CHECKED_OUT_FILE}"]
    expected_ignore=["git","check-ignore","-v","${IGNORED_SENTINEL}"]
    if (value.get("schema_version") != "msae_independent_source_v9_acquisition_v1"
            or value.get("source_repo") != REPO or value.get("source_commit") != COMMIT
            or value.get("files") != expected_files or value.get("clone_argv") != expected_clone
            or value.get("checkout_argv") != expected_checkout or value.get("sparse_checkout_paths") != expected_files
            or value.get("environment") != expected_environment
            or value.get("variables_required_absent") != expected_proxy_names
            or value.get("required_runtime_input") != "authority_review_sha256"
            or value.get("review_argument_flag") != "--authority-review-sha256"
            or value.get("head_argv") != expected_head or value.get("tree_argv") != expected_tree
            or value.get("ls_tree_argv") != expected_ls_tree or value.get("hash_object_argv") != expected_hash_object
            or value.get("ignore_argv") != expected_ignore
            or value.get("stdout_policy") != "quiet_hash_only_no_source_content"
            or value.get("stderr_policy") != "quiet_hash_only_no_source_content"):
        raise GateFailure("acquisition_config_drift")
    return value


def verify_v8_carryover(*, hash_raw: bool = True) -> dict[str, Any]:
    path = ROOT / CARRYOVER_PATH
    regular_state_nofollow(path, mode=0o644, nlink=1)
    if sha_file(path) != CARRYOVER_SHA256:
        raise GateFailure("v8_carryover_authority_drift")
    value = strict_json(path)
    exact_keys(value, {
        "schema_version", "status", "v8_source_commit", "v8_control_files",
        "v8_control_map_sha256", "v8_direct_predecessor_sha256",
        "v8_direct_predecessor_map_sha256", "v8_data_directories", "v8_raw_files",
        "v8_raw_file_map_sha256", "v8_acquisition_sha256", "v8_rejection_sha256",
        "v8_terminal_review_sha256", "v8_source_content_semantically_read_for_this_record",
        "v8_source_content_printed", "opaque_hash_reads", "quarantine_content_reads",
        "model_operations", "gpu_queries", "training_runs", "model_scoring_authorized",
        "k2_or_branch_training_authorized", "stage_c_authorized",
    }, "v8_carryover_authority_schema")
    if (value["schema_version"] != "msae_independent_source_v9_v8_carryover_authority_v1"
            or value["status"] != "retained_v8_control_plane_rejection_before_semantic_source_parse"
            or value["v8_source_commit"] != COMMIT
            or value["v8_control_map_sha256"] != "ecfdffb24efac47c4f8b7e7e2435759d10f2f652f60ebc48962c7148f7985f3d"
            or value["v8_direct_predecessor_map_sha256"] != "1dc8b1f85e6deb20edb63ec86da06e6cda64dca342223ed0d6d3fc9af7169a53"
            or value["v8_raw_file_map_sha256"] != "822d7d795020101b1554d5a25d87c229d1bd6cdf1926a42f3dfbf3f230b58e0e"
            or value["v8_acquisition_sha256"] != "6e57111da0b139bb2c4f0333b230b0a72458d7c419d50cfcb6896596b7f62958"
            or value["v8_rejection_sha256"] != "6352d5a52628898cbc1c4f91bbd97dfddf0aff48dd4c1422bc5d82517b33ad52"
            or value["v8_terminal_review_sha256"] != "fd3a40ba2ddd17a5a3464a669de186fdc4266307349751d81b01d6106ad7fc52"
            or value["v8_source_content_semantically_read_for_this_record"] is not False
            or value["v8_source_content_printed"] is not False
            or value["opaque_hash_reads"] != 4 or value["quarantine_content_reads"] != 0
            or value["model_operations"] != 0 or value["gpu_queries"] != 0
            or value["training_runs"] != 0 or value["model_scoring_authorized"] is not False
            or value["k2_or_branch_training_authorized"] is not False
            or value["stage_c_authorized"] is not False):
        raise GateFailure("v8_carryover_authority_drift")
    controls = value["v8_control_files"]
    if (not isinstance(controls, list) or len(controls) != 17
            or {item.get("path") for item in controls} != V8_CONTROL_PATHS):
        raise GateFailure("v8_control_universe_drift")
    control_map: dict[str, str] = {}
    for item in controls:
        exact_keys(item, {"path", "device", "inode", "mode", "nlink", "size", "sha256"},
                   "v8_control_record_schema")
        current = (ROOT / item["path"]).lstat()
        if (not stat.S_ISREG(current.st_mode) or stat.S_ISLNK(current.st_mode)
                or current.st_dev != item["device"] or current.st_ino != item["inode"]
                or stat.S_IMODE(current.st_mode) != item["mode"] or current.st_nlink != item["nlink"]
                or current.st_size != item["size"] or sha_file(ROOT / item["path"]) != item["sha256"]):
            raise GateFailure("v8_control_file_drift")
        control_map[item["path"]] = item["sha256"]
    if sha_bytes(_canonical_ascii_bytes(control_map)) != value["v8_control_map_sha256"]:
        raise GateFailure("v8_control_map_drift")
    predecessors = value["v8_direct_predecessor_sha256"]
    if (not isinstance(predecessors, dict) or len(predecessors) != 50
            or sha_bytes(_canonical_ascii_bytes(predecessors)) != value["v8_direct_predecessor_map_sha256"]
            or any(sha_file(ROOT / rel) != digest for rel, digest in predecessors.items())):
        raise GateFailure("v8_direct_predecessor_drift")
    directories = value["v8_data_directories"]
    expected_dirs = [
        "data/msae_independent_source_v8",
        "data/msae_independent_source_v8/raw",
        f"data/msae_independent_source_v8/raw/{COMMIT}",
    ]
    if [item.get("path") for item in directories] != expected_dirs:
        raise GateFailure("v8_data_directory_universe_drift")
    for item in directories:
        exact_keys(item, {"path", "device", "inode", "mode", "nlink", "size"},
                   "v8_data_directory_schema")
        current = (ROOT / item["path"]).lstat()
        if (not stat.S_ISDIR(current.st_mode) or stat.S_ISLNK(current.st_mode)
                or current.st_dev != item["device"] or current.st_ino != item["inode"]
                or stat.S_IMODE(current.st_mode) != item["mode"] or current.st_nlink != item["nlink"]):
            raise GateFailure("v8_data_directory_drift")
    raw = value["v8_raw_files"]
    expected_names = sorted((*SOURCE_FILES.values(), "LICENSE.txt"))
    raw_dir = ROOT / f"data/msae_independent_source_v8/raw/{COMMIT}"
    if sorted(item.get("path", "").rsplit("/", 1)[-1] for item in raw) != expected_names:
        raise GateFailure("v8_raw_universe_drift")
    _raw_stat,current_raw_names=directory_snapshot_nofollow(raw_dir)
    if current_raw_names != expected_names:
        raise GateFailure("v8_raw_extra_path")
    raw_map: dict[str, dict[str, Any]] = {}
    for item in raw:
        exact_keys(item, {"path", "device", "inode", "mode", "nlink", "size", "sha256", "git_blob_sha1"},
                   "v8_raw_record_schema")
        current = (ROOT / item["path"]).lstat()
        if (not stat.S_ISREG(current.st_mode) or stat.S_ISLNK(current.st_mode)
                or current.st_dev != item["device"] or current.st_ino != item["inode"]
                or stat.S_IMODE(current.st_mode) != item["mode"] or current.st_nlink != item["nlink"]
                or current.st_size != item["size"]):
            raise GateFailure("v8_raw_metadata_drift")
        if hash_raw and sha_file(ROOT / item["path"]) != item["sha256"]:
            raise GateFailure("v8_raw_hash_drift")
        raw_map[item["path"]] = {key: item[key] for key in
                                 ("sha256", "size", "git_blob_sha1", "mode", "nlink")}
    raw_after,raw_names_after=directory_snapshot_nofollow(raw_dir)
    if (_directory_fingerprint(_raw_stat)!=_directory_fingerprint(raw_after)
            or raw_names_after!=expected_names):
        raise GateFailure("v8_raw_metadata_drift")
    if sha_bytes(_canonical_ascii_bytes(raw_map)) != value["v8_raw_file_map_sha256"]:
        raise GateFailure("v8_raw_map_drift")
    return value


def _predecessor_hashes(*, hash_raw: bool = True) -> dict[str, str]:
    carryover = verify_v8_carryover(hash_raw=hash_raw)
    values = dict(carryover["v8_direct_predecessor_sha256"])
    for item in carryover["v8_control_files"]:
        previous = values.setdefault(item["path"], item["sha256"])
        if previous != item["sha256"]:
            raise GateFailure("v8_predecessor_collision")
    return dict(sorted(values.items()))

def _require_ship_review(path: Path, required_hashes: Iterable[str]) -> str:
    text = read_text_nofollow(path)
    if not text.startswith("VERDICT: SHIP") or any(value not in text for value in required_hashes):
        raise GateFailure("review_binding_ineligible")
    return sha_file(path)


def _json_text_fields(value: Any) -> list[tuple[str, ...]]:
    if not isinstance(value, dict):
        return []
    fields = ("source_words", "target_words", "words", "tokens", "text", "sentence")
    present = [name for name in fields if name in value]
    if any(name in present for name in ("source_words", "target_words")):
        if set(present) != {"source_words", "target_words"}:
            raise GateFailure("mixed_paired_json_text")
        return [_json_tokens(value["source_words"]), _json_tokens(value["target_words"])]
    if not present:
        return []
    values = [_json_tokens(value[name]) for name in present]
    if any(item != values[0] for item in values[1:]):
        raise GateFailure("conflicting_json_text_fields")
    return [values[0]]


def _json_tokens(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return lexical_tokens(value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(token for item in value for token in lexical_tokens(item))
    raise GateFailure("invalid_json_text_field")


def _update_json_census(value: dict[str,Any], fields: list[tuple[str,...]], census: dict[str,int]) -> None:
    names=[name for name in ("source_words","target_words","words","tokens","text","sentence") if name in value]
    census["structured_fields"]=census.get("structured_fields",0)+len(names)
    if set(names)=={"source_words","target_words"}:
        included=sum(bool(tokens) for tokens in fields)
    else:
        included=len(names) if fields and fields[0] else 0
    census["included_fields"]=census.get("included_fields",0)+included
    census["named_nontext_fields"]=census.get("named_nontext_fields",0)+len(names)-included


def parse_feats(value: str) -> dict[str, str]:
    if value == "_":
        return {}
    result: dict[str, str] = {}
    for item in value.split("|"):
        if item.count("=") != 1:
            raise GateFailure("malformed_feats")
        key, val = item.split("=", 1)
        values = val.split(",")
        if (not key or not val or key in result or "|" in val or "=" in val
                or any(not x for x in values) or len(set(values)) != len(values)
                or values != sorted(values)):
            raise GateFailure("malformed_feats")
        result[key] = val
    if "Number" in result and result["Number"] not in NUMBER:
        raise GateFailure("unknown_number")
    return result


def canonical_group_id(value: str) -> str:
    value = unicodedata.normalize("NFKC", value.strip()).casefold()
    if not value or "\0" in value:
        raise GateFailure("invalid_document_group_id")
    return value


def _finish_sentence(rows: list[Token], sent_id: str | None, index: int,
                     group_id: str | None) -> Sentence:
    if not rows or not sent_id or any(x in sent_id for x in ("\0", "\n", "\r")):
        raise GateFailure("invalid_sentence_identity")
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
    return Sentence(sent_id, tuple(rows), index, group_id)


def parse_conllu(path: Path) -> tuple[list[Sentence], dict[str, int]]:
    try:
        text = read_text_nofollow(path)
    except UnicodeError as e:
        raise GateFailure("invalid_utf8") from e
    rows: list[Token] = []
    sentences: list[Sentence] = []
    sent_id: str | None = None
    seen_ids: set[str] = set()
    seen_groups: set[str] = set()
    current_group: str | None = None
    marker_seen = False
    current_group_sentences = 0
    counts = {"integer_tokens": 0, "multiword_rows": 0, "empty_node_rows": 0}
    def flush() -> None:
        nonlocal rows, sent_id, current_group_sentences
        if not rows and sent_id is None:
            return
        sentence = _finish_sentence(rows, sent_id, len(sentences), current_group)
        if sentence.sent_id in seen_ids:
            raise GateFailure("duplicate_sent_id")
        seen_ids.add(sentence.sent_id)
        sentences.append(sentence)
        current_group_sentences += 1
        rows = []
        sent_id = None
    for line in text.splitlines():
        if not line:
            flush(); continue
        if line.startswith("#"):
            if line.startswith("# newdoc id = "):
                flush()
                if marker_seen and current_group_sentences == 0:
                    raise GateFailure("empty_document_group")
                value = canonical_group_id(line[len("# newdoc id = "):])
                if value in seen_groups:
                    raise GateFailure("duplicate_document_group_id")
                seen_groups.add(value); current_group = value; marker_seen = True
                current_group_sentences = 0
                continue
            if line.casefold().lstrip().startswith("# newdoc"):
                raise GateFailure("malformed_document_group_marker")
            if line.startswith("# sent_id = "):
                if sent_id is not None:
                    raise GateFailure("duplicate_sent_id_comment")
                sent_id = line[len("# sent_id = "):]
            continue
        cols = line.split("\t")
        if len(cols) != 10:
            raise GateFailure("malformed_conllu_columns")
        rid = cols[0]
        if "-" in rid:
            counts["multiword_rows"] += 1; continue
        if "." in rid:
            counts["empty_node_rows"] += 1; continue
        try:
            tid, head = int(rid), int(cols[6])
        except ValueError as e:
            raise GateFailure("malformed_integer") from e
        form, lemma, upos, feats, deprel = cols[1], cols[2], cols[3], cols[5], cols[7]
        if not form or lemma == "_" or not lemma or upos not in UPOS or not deprel:
            raise GateFailure("missing_or_unknown_field")
        coarse = deprel.split(":", 1)[0]
        if coarse not in DEPREL:
            raise GateFailure("unknown_deprel")
        parse_feats(feats)
        rows.append(Token(tid, unicodedata.normalize("NFC", form), unicodedata.normalize("NFC", lemma), upos, feats, head, deprel))
        counts["integer_tokens"] += 1
    flush()
    if marker_seen and current_group_sentences == 0:
        raise GateFailure("empty_document_group")
    if not sentences:
        raise GateFailure("empty_source")
    if marker_seen:
        if any(sentence.group_id is None for sentence in sentences):
            raise GateFailure("orphan_document_group_sentence")
    else:
        sentences = [dataclasses.replace(sentence,
                     group_id="sent_id_as_group:" + canonical_group_id(sentence.sent_id))
                     for sentence in sentences]
        if len({sentence.group_id for sentence in sentences}) != len(sentences):
            raise GateFailure("duplicate_fallback_document_group_id")
    return sentences, counts


def _cap(form: str) -> str:
    letters = "".join(c for c in form if c.isalpha())
    if not letters: return "nonalpha"
    if letters.islower(): return "lower"
    if letters.isupper(): return "upper"
    if letters.istitle(): return "title"
    return "mixed"


def _length(form: str) -> str:
    n = len(unicodedata.normalize("NFC", form))
    return "1" if n == 1 else "2" if n == 2 else "3_4" if n <= 4 else "5_7" if n <= 7 else "8p"


def _depth(token_id: int, heads: dict[int, int]) -> str:
    depth = 0; cur = token_id
    while heads[cur]:
        cur = heads[cur]; depth += 1
    return str(depth) if depth <= 3 else "4p"


def sentence_labels(sentence: Sentence) -> list[dict[str, str | None]]:
    n = len(sentence.tokens); heads = {x.id: x.head for x in sentence.tokens}
    out = []
    for tok in sentence.tokens:
        i = tok.id; d = tok.head - i
        head = "ROOT" if tok.head == 0 else ("L" if d < 0 else "R") + ("1_2" if abs(d) <= 2 else "3_4" if abs(d) <= 4 else "5p")
        boundary = "single" if n == 1 else "initial" if i == 1 else "final" if i == n else "interior"
        feats = parse_feats(tok.feats)
        out.append({
            "absolute_bucket": str(min(7, i - 1)),
            "relative_quartile": str(min(3, 4 * (i - 1) // n)),
            "token_identity": tok.form.casefold(), "lemma_identity": tok.lemma.casefold(),
            "capitalization": _cap(tok.form), "word_length": _length(tok.form),
            "punctuation": "PUNCT" if tok.form and all(unicodedata.category(c).startswith("P") for c in tok.form) else "NONPUNCT",
            "sentence_boundary": boundary, "head_signed_distance": head,
            "dependency_depth": _depth(i, heads), "upos_coarse": tok.upos,
            "deprel_coarse": tok.deprel.split(":", 1)[0], "number": feats.get("Number"),
        })
    return out


def normalized_sentence(sentence: Sentence) -> str:
    return " ".join(unicodedata.normalize("NFKC", x.form).casefold() for x in sentence.tokens)


def lexical_tokens(text: str) -> tuple[str, ...]:
    return tuple(x.casefold() for x in LEX.findall(unicodedata.normalize("NFKC", text)))


def fivegrams(tokens: tuple[str, ...]) -> set[tuple[str, ...]]:
    return {tokens[i:i+5] for i in range(max(0, len(tokens) - 4))}


def overlap_reason(candidate: tuple[str, ...], other: tuple[str, ...]) -> str | None:
    if not candidate or not other:
        return None
    if candidate == other:
        return "exact"
    if len(candidate) <= 9 and len(other) > len(candidate):
        if any(other[i:i+len(candidate)] == candidate for i in range(len(other) - len(candidate) + 1)):
            return "contained_short"
    if len(candidate) >= 10 and len(other) >= 10:
        a, b = fivegrams(candidate), fivegrams(other)
        shared = a & b
        if shared and len(shared) / len(a | b) >= .8:
            return "fivegram_jaccard"
        covered: set[int] = set()
        for i in range(len(candidate) - 4):
            if candidate[i:i+5] in b:
                covered.update(range(i, i + 5))
        if len(shared) >= 4 and len(covered) >= 20 and len(covered) / len(candidate) >= .1:
            return "covered_fivegrams"
    return None


def group_split_key(group_id: str, source_commit: str = COMMIT) -> str:
    if "\0" in group_id:
        raise GateFailure("nul_split_key")
    return sha_bytes(canonical_bytes(
        ["msae-independent-source-v9/C1C2-group", source_commit, group_id]))


def assign_split(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        group_id = row.get("group_id")
        if not isinstance(group_id, str) or not group_id:
            raise GateFailure("missing_split_group")
        groups[group_id].append(row)
    keyed = sorted(((group_split_key(group_id), group_id) for group_id in groups),
                   key=lambda item: (item[0], item[1].encode("utf-8")))
    assigned: list[dict[str, Any]] = []
    for group_rank, (key, group_id) in enumerate(keyed):
        panel = "C1" if group_rank % 2 == 0 else "C2"
        for within_rank, row in enumerate(sorted(groups[group_id],
                                                  key=lambda item: str(item["sent_id"]).encode("utf-8"))):
            assigned.append({**row, "group_key_sha256": key,
                             "group_id_sha256": sha_bytes(group_id.encode("utf-8")),
                             "group_rank": group_rank, "within_group_rank": within_rank,
                             "panel": panel})
    return assigned


def build_split_manifest(rows: list[dict[str, Any]], dedup: dict[str, Any],
                         census: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build and internally close the prospective group-level C1/C2 manifest."""
    test_rows=sorted(rows,key=lambda item:(item["group_rank"],item["within_group_rank"]))
    group_stats=exact_keys(dedup.get("test_groups"),
        {"pre_dedup_group_count","retained_group_count","fully_removed_group_count",
         "fully_removed_group_ids_sha256"},"split_group_census")
    for name in ("pre_dedup_group_count","retained_group_count","fully_removed_group_count"):
        if not _is_count(group_stats.get(name)):
            raise GateFailure("split_group_census")
    if (not _is_sha(group_stats.get("fully_removed_group_ids_sha256"))
            or group_stats["pre_dedup_group_count"] !=
               group_stats["retained_group_count"] + group_stats["fully_removed_group_count"]):
        raise GateFailure("split_group_census")
    by_rank: dict[int,list[dict[str,Any]]] = collections.defaultdict(list)
    for row in test_rows:
        rank=row.get("group_rank")
        if not _is_count(rank):raise GateFailure("split_group_rank")
        by_rank[rank].append(row)
    group_count=group_stats["retained_group_count"]
    if sorted(by_rank)!=list(range(group_count)):
        raise GateFailure("split_group_rank")
    for rank,group_rows in by_rank.items():
        expected_panel="C1" if rank%2==0 else "C2"
        if ([item.get("within_group_rank") for item in group_rows]!=list(range(len(group_rows)))
                or any(item.get("panel")!=expected_panel for item in group_rows)
                or len({item.get("group_key_sha256") for item in group_rows})!=1
                or len({item.get("group_id_sha256") for item in group_rows})!=1
                or any(not _is_sha(item.get("group_key_sha256"))
                       or not _is_sha(item.get("group_id_sha256")) for item in group_rows)):
            raise GateFailure("split_group_closure")
    c1_groups=sum(rank%2==0 for rank in by_rank)
    c2_groups=sum(rank%2==1 for rank in by_rank)
    if group_count<2 or c1_groups<1 or c2_groups<1:
        raise GateFailure("insufficient_split_groups")
    split={"schema_version":"msae_independent_source_v9_split_manifest_v1","source_commit":COMMIT,
           "upstream_partition":"test","test_group_policy":census["test_group_policy"],
           "split_algorithm":"sha256-canonical-json-group-v1-even-C1-odd-C2",
           "pre_dedup_group_count":group_stats["pre_dedup_group_count"],
           "retained_group_count":group_count,
           "fully_removed_group_count":group_stats["fully_removed_group_count"],
           "group_count":group_count,"C1_group_count":c1_groups,"C2_group_count":c2_groups,
           "record_count":len(test_rows),"C1_count":sum(item["panel"]=="C1" for item in test_rows),
           "C2_count":sum(item["panel"]=="C2" for item in test_rows),
           "entries":[{"sent_id":item["sent_id"],"panel":item["panel"],
                       "group_rank":item["group_rank"],"within_group_rank":item["within_group_rank"],
                       "group_key_sha256":item["group_key_sha256"],
                       "group_id_sha256":item["group_id_sha256"],
                       "source_record_sha256":_source_record_hash(item["sentence"])}
                      for item in test_rows]}
    return split,test_rows


def payload_record(row: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version":"msae_independent_source_v9_payload_v1","source_repo":REPO,
            "source_commit":COMMIT,"upstream_partition":"test","panel":row["panel"],
            "group_key_sha256":row["group_key_sha256"],"group_id_sha256":row["group_id_sha256"],
            "group_rank":row["group_rank"],"within_group_rank":row["within_group_rank"],
            "sent_id":row["sent_id"],"tokens":_token_objects(row["sentence"])}


def public_label(task: str, value: str) -> str:
    if task == "token_identity": return sha_bytes(("msae-v9/token\0" + value).encode())
    if task == "lemma_identity": return sha_bytes(("msae-v9/lemma\0" + value).encode())
    return value


def publish_private_jsonl(directory: Path, name: str, records: Iterable[dict[str, Any]]) -> Path:
    if Path(name).name != name or not name:
        raise GateFailure("invalid_payload_name")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent_fd=-1
    try:
        directory.relative_to(ROOT)
    except ValueError:
        directory.parent.mkdir(parents=True,exist_ok=True)
        parent_fd=os.open(directory.parent,flags)
    else:
        parent_fd=open_repo_dir(directory.parent)
    try:
        try:os.mkdir(directory.name,0o700,dir_fd=parent_fd);os.fsync(parent_fd)
        except FileExistsError:pass
        try:dfd=os.open(directory.name,flags,dir_fd=parent_fd)
        except OSError as error:raise GateFailure("unsafe_payload_directory") from error
    finally:os.close(parent_fd)
    directory_stat=os.fstat(dfd)
    if stat.S_IMODE(directory_stat.st_mode)!=0o700:
        os.fchmod(dfd,0o700);os.fsync(dfd);directory_stat=os.fstat(dfd)
    target_name = name
    tmp_name = "." + name + ".building"
    target = directory / name
    try:
        for candidate, code in ((tmp_name, "abandoned_payload_temporary"), (target_name, "payload_already_exists")):
            try:
                os.stat(candidate, dir_fd=dfd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise GateFailure(code)
        fd = os.open(tmp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=dfd)
        created=os.fstat(fd);identity=(created.st_dev,created.st_ino)
        try:
            os.fchmod(fd, 0o600)
            for row in records:
                data = canonical_file_bytes(row)
                pos = 0
                while pos < len(data):
                    written=os.write(fd,data[pos:])
                    if written<=0:raise OSError("short payload write")
                    pos+=written
            os.fsync(fd)
        except BaseException:
            os.close(fd)
            cleanup_created_temp(dfd,tmp_name,identity)
            raise
        else:
            os.close(fd)
        try:
            os.link(tmp_name, target_name, src_dir_fd=dfd, dst_dir_fd=dfd, follow_symlinks=False)
        except BaseException:
            cleanup_created_temp(dfd,tmp_name,identity)
            raise
        linked = os.stat(target_name, dir_fd=dfd, follow_symlinks=False)
        temporary = os.stat(tmp_name, dir_fd=dfd, follow_symlinks=False)
        if ((linked.st_dev,linked.st_ino)!=(temporary.st_dev,temporary.st_ino)
                or not stat.S_ISREG(linked.st_mode) or stat.S_IMODE(linked.st_mode)!=0o600
                or linked.st_nlink!=2):
            raise GateFailure("payload_link_verification")
        cleanup_created_temp(dfd,tmp_name,identity)
        final = os.stat(target_name, dir_fd=dfd, follow_symlinks=False)
        if (not stat.S_ISREG(final.st_mode) or stat.S_IMODE(final.st_mode)!=0o600 or final.st_nlink!=1
                or (os.fstat(dfd).st_dev,os.fstat(dfd).st_ino)!=(directory_stat.st_dev,directory_stat.st_ino)):
            raise GateFailure("payload_final_verification")
        os.fsync(dfd)
    finally:
        os.close(dfd)
    return target


def _file_hash_and_text(path: Path) -> tuple[str, bool]:
    fd=open_repo_file(path)
    try:
        before=os.fstat(fd);digest,is_text=_hash_and_text_fd(fd);after=os.fstat(fd)
        if _stat_fingerprint(before)!=_stat_fingerprint(after):
            raise GateFailure("file_mutated_while_reading")
        return digest,is_text
    finally:os.close(fd)


def _is_utf8(payload: bytes) -> bool:
    try:
        return "\0" not in payload.decode("utf-8")
    except UnicodeDecodeError:
        return False


def _safe_member_name(name: str) -> bool:
    pure = Path(name)
    return bool(name) and not pure.is_absolute() and ".." not in pure.parts and "\0" not in name


def _archive_kind(payload: bytes) -> str | None:
    if payload.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    if payload.startswith(b"\x1f\x8b"):
        return "gzip"
    if len(payload) >= 265 and payload[257:262] == b"ustar":
        return "tar"
    return None


def _opaque_member_matches_suffix(name: str, payload: bytes) -> bool:
    suffix = Path(name).suffix.lower()
    signatures = {
        ".png": (b"\x89PNG\r\n\x1a\n",), ".pdf": (b"%PDF-",),
        ".npy": (b"\x93NUMPY",), ".npz": (b"PK\x03\x04",),
        ".zip": (b"PK\x03\x04",), ".gz": (b"\x1f\x8b",),
        ".pkl": (b"\x80",), ".parquet": (b"PAR1",),
        ".feather": (b"ARROW1",), ".orc": (b"ORC",),
    }
    if suffix == ".pyc":
        return len(payload) >= 16 and payload.startswith(b"\xcb\r\r\n")
    return suffix in signatures and payload.startswith(signatures[suffix])


def _stat_fingerprint(value: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (value.st_dev,value.st_ino,value.st_mode,value.st_nlink,value.st_size,
            value.st_mtime_ns,value.st_ctime_ns)


def _directory_fingerprint(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    """Fingerprint a directory without its filesystem-dependent st_size view."""
    return (value.st_dev,value.st_ino,value.st_mode,value.st_nlink,
            value.st_mtime_ns,value.st_ctime_ns)


def _hash_fd(fd: int) -> str:
    os.lseek(fd,0,os.SEEK_SET);digest=hashlib.sha256()
    while True:
        block=os.read(fd,1024*1024)
        if not block:break
        digest.update(block)
    return digest.hexdigest()


def _hash_and_text_fd(fd: int) -> tuple[str,bool]:
    os.lseek(fd,0,os.SEEK_SET);digest=hashlib.sha256()
    decoder=codecs.getincrementaldecoder("utf-8")("strict");is_text=True
    while True:
        block=os.read(fd,1024*1024)
        if not block:break
        digest.update(block)
        if b"\0" in block:is_text=False
        if is_text:
            try:decoder.decode(block,final=False)
            except UnicodeDecodeError:is_text=False
    if is_text:
        try:decoder.decode(b"",final=True)
        except UnicodeDecodeError:is_text=False
    return digest.hexdigest(),is_text


def _archive_analysis(path: Path, expected: os.stat_result | None = None) -> tuple[str,list[tuple[str,bytes]] | None]:
    """Hash and parse one bound no-follow archive inode, rejecting path or in-place drift."""
    try:fd=open_repo_file(path)
    except OSError as error:raise GateFailure("unsafe_archive_open") from error
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or (expected is not None and _stat_fingerprint(before)!=_stat_fingerprint(expected)):
            raise GateFailure("archive_path_identity_drift")
        digest=_hash_fd(fd);probe=os.pread(fd,512,0)
        limit=1<<30;members: list[tuple[str,bytes]]=[];outside_bounds=False
        suffixes=[value.lower() for value in path.suffixes]
        expected_kind=("zip" if path.suffix.lower()==".zip" else "gzip" if path.suffix.lower()==".gz"
                       else "tar" if ".tar" in suffixes else None)
        if expected_kind is None or _archive_kind(probe)!=expected_kind:
            raise GateFailure("archive_magic_suffix_mismatch")
        try:
            os.lseek(fd,0,os.SEEK_SET)
            with os.fdopen(os.dup(fd),"rb") as archive_handle:
                if path.suffix.lower()==".zip":
                    with zipfile.ZipFile(archive_handle) as archive:
                        infos=archive.infolist()
                        if len(infos)>100_000:outside_bounds=True
                        total=sum(item.file_size for item in infos)
                        if total>limit or total>max(1,before.st_size)*20:outside_bounds=True
                        if not outside_bounds:
                            for item in infos:
                                mode=(item.external_attr>>16)&0o170000
                                if (item.is_dir() or item.flag_bits&1 or not _safe_member_name(item.filename)
                                        or mode not in (0,stat.S_IFREG)):
                                    raise GateFailure("unsafe_archive_member")
                                members.append((item.filename,archive.read(item)))
                elif ".tar" in suffixes:
                    with tarfile.open(fileobj=archive_handle,mode="r:*") as archive:
                        infos=archive.getmembers()
                        if len(infos)>100_000:outside_bounds=True
                        if any(not item.isfile() or not _safe_member_name(item.name) for item in infos):
                            raise GateFailure("unsafe_archive_member")
                        total=sum(item.size for item in infos)
                        if total>limit or total>max(1,before.st_size)*20:outside_bounds=True
                        if not outside_bounds:
                            for item in infos:
                                handle=archive.extractfile(item)
                                if handle is None:raise GateFailure("unsafe_archive_member")
                                members.append((item.name,handle.read()))
                elif path.suffix.lower()==".gz":
                    with gzip.GzipFile(fileobj=archive_handle,mode="rb") as handle:
                        payload=handle.read(limit+1)
                    if len(payload)>limit or len(payload)>max(1,before.st_size)*20:outside_bounds=True
                    else:members.append((path.stem,payload))
                else:raise GateFailure("unknown_archive")
        except (OSError,EOFError,tarfile.TarError,zipfile.BadZipFile) as error:
            raise GateFailure("invalid_archive") from error
        for name,payload in members:
            suffix=Path(name).suffix.lower()
            if suffix in {".zip",".tar",".gz",".tgz"} or _archive_kind(payload) is not None:
                raise GateFailure("nested_archive")
            try:text="\0" not in payload.decode("utf-8")
            except UnicodeDecodeError:text=False
            if not text and not _opaque_member_matches_suffix(name,payload):
                raise GateFailure("unsupported_archive_member")
        after=os.fstat(fd)
        try:current=path.lstat()
        except OSError as error:raise GateFailure("archive_path_identity_drift") from error
        if _stat_fingerprint(before)!=_stat_fingerprint(after) or _stat_fingerprint(before)!=_stat_fingerprint(current):
            raise GateFailure("archive_path_identity_drift")
        return digest,None if outside_bounds else members
    finally:os.close(fd)


def archive_members(path: Path) -> list[tuple[str, bytes]] | None:
    """Return one-level safe archive members, None when a valid archive exceeds frozen bounds."""
    return _archive_analysis(path)[1]


def inventory_one(path: Path, rel: str, quarantines: set[str]) -> dict[str, Any]:
    s = path.lstat()
    base = {"path": rel, "size": s.st_size, "mode": stat.S_IMODE(s.st_mode), "device": s.st_dev,
            "inode": s.st_ino, "nlink": s.st_nlink, "mtime_ns": s.st_mtime_ns}
    if rel in quarantines:
        return {**base, "sha256": None, "disposition": "quarantine", "adapter": "quarantine_lstat_only",
                "content_reads": 0, "extracted_unit_count": 0}
    if path.suffix.lower() in {".zip", ".gz", ".tar"} or ".tar" in {x.lower() for x in path.suffixes}:
        digest,members = _archive_analysis(path,s)
        if members is None:
            return {**base, "sha256": digest, "disposition": "binary_unscanned",
                    "adapter": "opaque_archive_outside_bounds", "content_reads": 1,
                    "extracted_unit_count": 0, "archive_member_count": None}
        return {**base, "sha256": digest, "disposition": "archive_scanned",
                "adapter": "safe_archive_members", "content_reads": 1,
                "extracted_unit_count": 0, "archive_member_count": len(members),
                "archive_members_sha256": sha_bytes(canonical_bytes([
                    {"name": name, "sha256": sha_bytes(payload), "size": len(payload)}
                    for name, payload in members]))}
    digest, text = _file_hash_and_text(path)
    try:after=path.lstat()
    except OSError as error:raise GateFailure("path_identity_changed") from error
    if _stat_fingerprint(s)!=_stat_fingerprint(after):raise GateFailure("path_identity_changed")
    if text:
        disp, adapter = "text_scanned", "conllu_sentences" if path.suffix.lower() == ".conllu" else "physical_lines"
    else:
        suffixes = {x.lower() for x in path.suffixes}
        if not suffixes & BINARY_SUFFIXES and path.suffix.lower() not in BINARY_SUFFIXES:
            disp, adapter = "terminal_unsupported", "none"
        else:
            disp, adapter = "binary_unscanned", "opaque_binary"
    return {**base, "sha256": digest, "disposition": disp, "adapter": adapter,
            "content_reads": 1, "extracted_unit_count": 0}


def _walk_descriptor_paths(*, include_v9: bool, reject_v9_namespace: bool
                           ) -> Iterator[tuple[Path, str]]:
    """Walk the repository through pinned directory descriptors.

    Each child directory is matched to the entry opened from its parent and is
    checked again after recursive enumeration.  A rename/replacement therefore
    cannot redirect a census to an unchecked ancestor.
    """
    root_before=ROOT.lstat();rootfd=open_repo_dir(ROOT)
    try:
        root_open=os.fstat(rootfd)
        if _directory_fingerprint(root_before)!=_directory_fingerprint(root_open):
            raise GateFailure("path_identity_changed")

        def visit(dfd: int, relbase: str) -> Iterator[tuple[Path,str]]:
            directory_before=os.fstat(dfd)
            try:names=sorted(os.listdir(dfd))
            except OSError as error:raise GateFailure("path_identity_changed") from error
            for name in names:
                rel=name if not relbase else relbase+"/"+name
                try:entry=os.stat(name,dir_fd=dfd,follow_symlinks=False)
                except OSError as error:raise GateFailure("path_identity_changed") from error
                if stat.S_ISLNK(entry.st_mode):raise GateFailure("special_paths")
                if stat.S_ISDIR(entry.st_mode):
                    if (name=="__pycache__" or any((rel+"/").startswith(x) for x in GENERATED_PREFIXES)
                            or rel==V8_DATA_PREFIX.rstrip("/")
                            or (not include_v9 and rel==V9_PREFIX.rstrip("/"))):
                        if reject_v9_namespace and rel==V9_PREFIX.rstrip("/"):
                            childfd=os.open(name,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0),dir_fd=dfd)
                            try:
                                child_open=os.fstat(childfd)
                                if (_directory_fingerprint(entry)!=_directory_fingerprint(child_open)
                                        or os.listdir(childfd)):
                                    raise GateFailure("preexisting_v9_namespace")
                                child_after=os.fstat(childfd)
                            finally:os.close(childfd)
                            current=os.stat(name,dir_fd=dfd,follow_symlinks=False)
                            if (_directory_fingerprint(entry)!=_directory_fingerprint(child_after)
                                    or _directory_fingerprint(entry)!=_directory_fingerprint(current)):
                                raise GateFailure("path_identity_changed")
                        continue
                    childfd=os.open(name,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0),dir_fd=dfd)
                    try:
                        child_open=os.fstat(childfd)
                        if _directory_fingerprint(entry)!=_directory_fingerprint(child_open):
                            raise GateFailure("path_identity_changed")
                        yield from visit(childfd,rel)
                        child_after=os.fstat(childfd)
                    finally:os.close(childfd)
                    current=os.stat(name,dir_fd=dfd,follow_symlinks=False)
                    if (_directory_fingerprint(entry)!=_directory_fingerprint(child_after)
                            or _directory_fingerprint(entry)!=_directory_fingerprint(current)):
                        raise GateFailure("path_identity_changed")
                    continue
                if rel.startswith(".git/"):continue
                if reject_v9_namespace and rel.startswith(V9_PREFIX):
                    raise GateFailure("preexisting_v9_namespace")
                yield ROOT/rel,rel
            if _directory_fingerprint(directory_before)!=_directory_fingerprint(os.fstat(dfd)):
                raise GateFailure("path_identity_changed")

        yield from visit(rootfd,"")
        root_after=os.fstat(rootfd);root_current=ROOT.lstat()
        if (_directory_fingerprint(root_open)!=_directory_fingerprint(root_after)
                or _directory_fingerprint(root_open)!=_directory_fingerprint(root_current)):
            raise GateFailure("path_identity_changed")
    finally:os.close(rootfd)


def _walk_paths() -> Iterator[tuple[Path, str]]:
    yield from _walk_descriptor_paths(include_v9=False,reject_v9_namespace=True)


def inventory_repository() -> dict[str, Any]:
    paths = list(_walk_paths())
    verify_v8_carryover()
    by_inode: dict[tuple[int, int], list[tuple[Path, str, os.stat_result]]] = collections.defaultdict(list)
    special = []
    for p, rel in paths:
        s = p.lstat()
        if stat.S_ISLNK(s.st_mode) or not stat.S_ISREG(s.st_mode):
            special.append(rel); continue
        by_inode[(s.st_dev, s.st_ino)].append((p, rel, s))
    if special: raise GateFailure("special_paths")
    entries = []
    for key in sorted(by_inode, key=lambda z: min(x[1] for x in by_inode[z])):
        group = sorted(by_inode[key], key=lambda z: z[1]); aliases = [x[1] for x in group]
        if group[0][2].st_nlink != len(group): raise GateFailure("external_hardlink_alias")
        if QUARANTINES.intersection(aliases) and len(group) != 1: raise GateFailure("quarantine_alias")
        rep = inventory_one(group[0][0], group[0][1], QUARANTINES)
        for _p, rel, s in group:
            item = dict(rep); item.update({"path": rel, "mode": stat.S_IMODE(s.st_mode), "size": s.st_size,
                                           "mtime_ns": s.st_mtime_ns, "nlink": s.st_nlink,
                                           "hardlink_aliases": aliases if len(aliases) > 1 else []})
            if rel in QUARANTINES: item = inventory_one(_p, rel, QUARANTINES)
            elif rel.startswith(V9_PREFIX): item.update(disposition="v9_excluded", adapter="excluded", extracted_unit_count=0)
            elif rel in V8_CONTROL_PATHS:
                item.update(disposition="v8_candidate_control_carryover", adapter="carryover",
                            extracted_unit_count=0)
            elif rel in V9_AUTHORITY:
                item.update(disposition="v9_authority", adapter="authority", extracted_unit_count=0)
            entries.append(item)
    counts = collections.Counter(x["disposition"] for x in entries)
    if counts["terminal_unsupported"]: raise GateFailure("unsupported_files")
    return {"schema_version": "msae_independent_source_v9_baseline_inventory_v1",
            "baseline_head": "7e1a6fc7a26a870a4edcf29c96b7cdf3cdbd7faa",
            "entry_count": len(entries), "counts": dict(sorted(counts.items())),
            "quarantine_content_reads": 0, "entries": entries,
            "v8_carryover_authority_sha256": CARRYOVER_SHA256,
            "v8_carryover_status": "opaque_exact_universe_verified",
            "authority_expected_absent": sorted(V9_AUTHORITY - {x["path"] for x in entries}),
            "entries_sha256": sha_bytes(canonical_bytes(entries)), "status": "eligible"}


def _canonical_ascii_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def history_input_records(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    if any(item.get("disposition") == "archive_scanned" for item in inventory.get("entries", [])):
        raise GateFailure("history_registry_archive_drift")
    records = [{"path": item["path"], "sha256": item["sha256"], "size": item["size"]}
               for item in inventory.get("entries", [])
               if item.get("disposition") == "text_scanned"]
    return sorted(records, key=lambda item: item["path"])


def validate_history_registry_binding(inventory: dict[str, Any],
                                      registry: dict[str, Any] | None = None,
                                      screen: dict[str, Any] | None = None) -> str:
    loaded_registry = registry is None
    if registry is None:
        registry = strict_json(PROV / "historical_source_registry.json")
    if screen is None:
        screen = strict_json(PROV / "preacquisition_alias_screen.json")
    records = history_input_records(inventory)
    digest = sha_bytes(_canonical_ascii_bytes(records))
    if (registry.get("schema_version") != "msae_independent_source_v9_historical_source_registry_v1"
            or ("history_inputs_sha256" in inventory and inventory.get("history_inputs_sha256") != digest)
            or registry.get("status") != "frozen_preacquisition"
            or registry.get("domain_utf8") != "msae-v9/pedigree"
            or registry.get("input_count") != len(records)
            or registry.get("inputs") != records
            or registry.get("inputs_sha256") != digest
            or registry.get("overbound_json_source_key_construct_count") != 0
            or screen.get("schema_version") != "msae_independent_source_v9_preacquisition_alias_screen_v2"
            or screen.get("history_input_count") != len(records)
            or screen.get("history_inputs_sha256") != digest
            or (loaded_registry and screen.get("history_registry_sha256")
                != sha_file(PROV / "historical_source_registry.json"))
            or screen.get("content_occurrence_count") != 0
            or screen.get("pathname_occurrence_count") != 0
            or screen.get("source_use_evidence_count") != 0
            or screen.get("status") != "no_project_source_use_evidence"):
        raise GateFailure("history_registry_input_drift")
    return digest


def _history_text_units(text: str, suffix: str, census: dict[str, int] | None = None) -> Iterator[tuple[str, ...]]:
    if census is None:
        census = collections.Counter()
    if suffix == ".conllu":
        words: list[str] = []
        for line in text.splitlines():
            if not line:
                if words: yield tuple(x for w in words for x in lexical_tokens(w)); words=[]
            elif not line.startswith("#"):
                cols = line.split("\t")
                if len(cols) == 10 and cols[0].isdigit(): words.append(cols[1])
        if words: yield tuple(x for w in words for x in lexical_tokens(w))
        return
    if suffix == ".jsonl":
        for line in text.splitlines():
            if not line.strip():
                continue
            value = strict_json_loads(line)
            if not isinstance(value, dict):
                raise GateFailure("invalid_jsonl_root")
            census["structured_rows"] = census.get("structured_rows", 0) + 1
            all_fields=_json_text_fields(value);_update_json_census(value,all_fields,census)
            fields = [tokens for tokens in all_fields if tokens]
            if fields:
                census["included_rows"] = census.get("included_rows", 0) + 1
                census["text_subrecords"] = census.get("text_subrecords", 0) + len(fields)
                yield from fields
            else:
                census["named_nontext_rows"] = census.get("named_nontext_rows", 0) + 1
            physical = lexical_tokens(line)
            if physical:
                census["physical_line_units"] = census.get("physical_line_units", 0) + 1
                yield physical
        return
    if suffix == ".json":
        value = strict_json_loads(text)
        if isinstance(value, list):
            rows = value
        elif isinstance(value, dict):
            keys = [key for key in ("records", "rows", "data") if key in value]
            if len(keys) != 1 or not isinstance(value[keys[0]], list):
                raise GateFailure("invalid_json_root")
            rows = value[keys[0]]
        else:
            raise GateFailure("invalid_json_root")
        for row in rows:
            if not isinstance(row, dict):
                raise GateFailure("invalid_json_row")
            census["structured_rows"] = census.get("structured_rows", 0) + 1
            all_fields=_json_text_fields(row);_update_json_census(row,all_fields,census)
            fields = [tokens for tokens in all_fields if tokens]
            if fields:
                census["included_rows"] = census.get("included_rows", 0) + 1
                census["text_subrecords"] = census.get("text_subrecords", 0) + len(fields)
                yield from fields
            else:
                census["named_nontext_rows"] = census.get("named_nontext_rows", 0) + 1
        for line in text.splitlines():
            physical = lexical_tokens(line)
            if physical:
                census["physical_line_units"] = census.get("physical_line_units", 0) + 1
                yield physical
        return
    for line in text.splitlines():
        tokens = lexical_tokens(line)
        if tokens:
            census["physical_line_units"] = census.get("physical_line_units", 0) + 1
            yield tokens


def _history_units(path: Path, adapter: str, census: dict[str, int] | None = None) -> Iterator[tuple[str, ...]]:
    if census is None:
        census = collections.Counter()
    if adapter == "safe_archive_members":
        members = archive_members(path)
        if members is None:
            raise GateFailure("archive_bound_drift")
        for name, payload in members:
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if "\0" in text:
                continue
            yield from _history_text_units(text, Path(name).suffix.lower(), census)
        return
    if path.suffix.lower() in {".json", ".conllu"}:
        yield from _history_text_units(read_text_nofollow(path), path.suffix.lower(), census)
        return
    if path.suffix.lower() == ".jsonl":
        for line in read_text_nofollow(path).splitlines(keepends=True):
            yield from _history_text_units(line, ".jsonl", census)
        return
    for line in read_text_nofollow(path).splitlines(keepends=True):
        yield from _history_text_units(line, path.suffix.lower(), census)


def validate_partition_group_ids(roles: dict[str, list[Sentence]]) -> None:
    explicit: dict[str, set[str]] = {}
    for role, sentences in roles.items():
        explicit[role] = {str(sentence.group_id) for sentence in sentences
                          if sentence.group_id is not None
                          and not sentence.group_id.startswith("sent_id_as_group:")}
    names = tuple(explicit)
    if any(explicit[left] & explicit[right] for i, left in enumerate(names)
           for right in names[i + 1:]):
        raise GateFailure("cross_partition_document_id")


def _all_source() -> tuple[dict[str, list[Sentence]], dict[str, Any]]:
    roles: dict[str, list[Sentence]] = {}
    counts = {}
    for upstream, name in SOURCE_FILES.items():
        sentences, c = parse_conllu(RAW / name)
        role = "discovery" if upstream == "train" else "calibration" if upstream == "dev" else "test"
        roles[role] = sentences; counts[upstream] = {**c, "sentences": len(sentences), "sha256": sha_file(RAW/name)}
    validate_partition_group_ids(roles)
    return roles, counts


def deduplicate_roles(roles: dict[str, list[Sentence]]) -> tuple[dict[str, list[Sentence]], dict[str, Any]]:
    upstream = {"discovery": "train", "calibration": "dev", "test": "test"}
    kept: dict[str, list[Sentence]] = {}
    within_dropped: dict[str, list[str]] = {}
    normalized_by_role: dict[str, set[str]] = {}
    for role in ("discovery", "calibration", "test"):
        groups: dict[str, list[Sentence]] = collections.defaultdict(list)
        for sentence in roles[role]:
            groups[normalized_sentence(sentence)].append(sentence)
        retained: list[Sentence] = []
        dropped: list[str] = []
        for normalized in sorted(groups):
            ordered = sorted(groups[normalized], key=lambda item: (item.sent_id.encode("utf-8"), item.source_index))
            retained.append(ordered[0]); dropped.extend(item.sent_id for item in ordered[1:])
        kept[role] = sorted(retained, key=lambda item: item.source_index)
        within_dropped[role] = sorted(dropped)
        normalized_by_role[role] = {normalized_sentence(item) for item in retained}
    shared = set()
    names = tuple(normalized_by_role)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            shared |= normalized_by_role[left] & normalized_by_role[right]
    cross_ids: dict[str, list[str]] = {}
    for role in names:
        removed = sorted(item.sent_id for item in kept[role] if normalized_sentence(item) in shared)
        cross_ids[role] = removed
        kept[role] = [item for item in kept[role] if normalized_sentence(item) not in shared]
    def ids_hash(values: list[str]) -> str:
        return sha_bytes(canonical_bytes(values))
    pre_test_groups={str(sentence.group_id) for sentence in roles["test"]}
    retained_test_groups={str(sentence.group_id) for sentence in kept["test"]}
    report = {"schema_version": "msae_independent_source_v9_dedup_v1", "roles": {},
              "cross_partition_normalized_group_count": len(shared), "source_text_published": False,
              "test_groups":{"pre_dedup_group_count":len(pre_test_groups),
                             "retained_group_count":len(retained_test_groups),
                             "fully_removed_group_count":len(pre_test_groups-retained_test_groups),
                             "fully_removed_group_ids_sha256":ids_hash(sorted(pre_test_groups-retained_test_groups))}}
    for role in names:
        report["roles"][role] = {
            "upstream_partition": upstream[role], "input_count": len(roles[role]),
            "retained_count": len(kept[role]), "within_partition_dropped_count": len(within_dropped[role]),
            "within_partition_dropped_ids_sha256": ids_hash(within_dropped[role]),
            "cross_partition_dropped_count": len(cross_ids[role]),
            "cross_partition_dropped_ids_sha256": ids_hash(cross_ids[role]),
        }
    return kept, report


def _source_rows(roles: dict[str, list[Sentence]]) -> dict[str, list[dict[str, Any]]]:
    test = assign_split([{"sent_id": s.sent_id, "group_id":s.group_id,
                          "normalized": normalized_sentence(s), "sentence": s} for s in roles["test"]])
    out = {"discovery": [{"sent_id":s.sent_id,"normalized":normalized_sentence(s),"sentence":s} for s in roles["discovery"]],
           "calibration": [{"sent_id":s.sent_id,"normalized":normalized_sentence(s),"sentence":s} for s in roles["calibration"]],
           "C1": [], "C2": []}
    for row in test: out[row["panel"]].append(row)
    return out


def _role_overlap(rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, str]]:
    roles = ("discovery", "calibration", "C1", "C2"); hits=[]
    for ai in range(len(roles)):
        for bi in range(ai+1,len(roles)):
            a,b=roles[ai],roles[bi]
            for ar in rows[a]:
                at=lexical_tokens(ar["normalized"])
                for br in rows[b]:
                    bt=lexical_tokens(br["normalized"])
                    for cr,ct,orr,ot in ((ar,at,br,bt),(br,bt,ar,at)):
                        reason=overlap_reason(ct,ot)
                        if reason: hits.append({"candidate_role":a if cr is ar else b,"candidate_id":cr["sent_id"],"other_role":b if orr is br else a,"other_id":orr["sent_id"],"reason":reason})
                        if len(hits)>=100:return hits
    return hits


def _history_overlap(rows: dict[str, list[dict[str, Any]]], inventory: dict[str, Any]) -> tuple[list[dict[str,str]], int, dict[str,int]]:
    candidates=[]
    for role, vals in rows.items():
        for row in vals: candidates.append((role,row["sent_id"],lexical_tokens(row["normalized"])))
    exact=collections.defaultdict(list); shorts=collections.defaultdict(lambda:collections.defaultdict(list)); inv=collections.defaultdict(set); unigrams=collections.defaultdict(set)
    for i,(role,sid,tok) in enumerate(candidates):
        exact[tok].append(i)
        if len(tok)<=9: shorts[len(tok)][tok].append(i)
        gs=fivegrams(tok)
        for g in gs: inv[g].add(i)
        for token in set(tok): unigrams[token].add(i)
    hits=[]; units=0; census: dict[str,int]=collections.Counter()
    by_path={x["path"]:x for x in inventory["entries"]}
    for rel,item in sorted(by_path.items()):
        if item["disposition"] not in {"text_scanned", "archive_scanned"}:continue
        p=ROOT/rel
        before=p.stat()
        count=0
        file_census: dict[str,int]=collections.Counter()
        for other in _history_units(p,item["adapter"],file_census):
            count+=1;units+=1
            ids=set(exact.get(other,()))
            for n,lookup in shorts.items():
                if len(other)>n:
                    for j in range(len(other)-n+1): ids.update(lookup.get(other[j:j+n],()))
            if len(other)<=9 and other:
                ids.update(unigrams.get(other[0],()))
            og=fivegrams(other)
            for g in og:ids.update(inv.get(g,()))
            for i in sorted(ids):
                role,sid,ct=candidates[i];reason=overlap_reason(ct,other) or overlap_reason(other,ct)
                if reason:hits.append({"role":role,"sent_id":sid,"history_path":rel,"reason":reason})
                if len(hits)>=100:
                    census.update(file_census)
                    return hits,units,dict(sorted(census.items()))
        item["extracted_unit_count"]=count
        census.update(file_census)
        after=p.stat()
        if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):raise GateFailure("history_mutated")
    if census.get("structured_rows",0) != census.get("included_rows",0) + census.get("named_nontext_rows",0):
        raise GateFailure("structured_history_census_mismatch")
    if census.get("structured_fields",0) != census.get("included_fields",0) + census.get("named_nontext_fields",0):
        raise GateFailure("structured_history_field_census_mismatch")
    return hits,units,dict(sorted(census.items()))


def _support(rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result={};intersection=set(TASKS)
    for role,vals in rows.items():
        per={}
        for task in TASKS:
            classes: dict[str,set[str]]=collections.defaultdict(set)
            for row in vals:
                for labels in sentence_labels(row["sentence"]):
                    val=labels[task]
                    if val is not None:classes[str(val)].add(row["sent_id"])
            retained={public_label(task,k):len(v) for k,v in classes.items() if len(v)>=20}
            eligible=len(retained)>=2
            per[task]={"eligible":eligible,"retained_class_count":len(retained),"distinct_utterances_by_class":dict(sorted(retained.items()))}
            if not eligible:intersection.discard(task)
        result[role]={"utterance_count":len(vals),"tasks":per}
    passed=REQUIRED<=intersection and len(OPTIONAL&intersection)>=2
    return {"schema_version":"msae_independent_source_v9_support_v1","floor_distinct_utterances":20,
            "roles":result,"all_role_task_intersection":sorted(intersection),"status":"eligible" if passed else "ineligible"}


def _token_objects(sentence: Sentence) -> list[dict[str,Any]]:
    return [{"id":t.id,"form":t.form,"lemma":t.lemma,"upos":t.upos,"head":t.head,"deprel":t.deprel,"feats":t.feats} for t in sentence.tokens]


def _source_record_hash(sentence: Sentence) -> str:
    return sha_bytes(canonical_bytes(_token_objects(sentence)))


URL_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~:/?#[]@!$&'()*+,;=%-")
LICENSE_URLS = {
    "http://creativecommons.org/licenses/by-sa/4.0",
    "http://creativecommons.org/licenses/by-sa/4.0/",
    "https://creativecommons.org/licenses/by-sa/4.0",
    "https://creativecommons.org/licenses/by-sa/4.0/",
}
LICENSE_PHRASES = (
    ("cc", "by", "sa", "4", "0"),
    ("creative", "commons", "attribution", "sharealike", "4", "0"),
    ("attribution", "sharealike", "4", "0", "international"),
)
LICENSE_CONTRADICTIONS = (
    ("all", "rights", "reserved"), ("no", "redistribution"),
    ("non", "commercial", "use", "only"),
)


def _contains_window(tokens: tuple[str, ...], window: tuple[str, ...]) -> int:
    return sum(tokens[index:index + len(window)] == window
               for index in range(len(tokens) - len(window) + 1))


def license_evidence(text: str) -> dict[str, Any]:
    if "\0" in text:
        raise GateFailure("license_nul")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens = tuple(LEX.findall(normalized))
    phrases = {" ".join(window): _contains_window(tokens, window)
               for window in LICENSE_PHRASES}
    contradictions = {" ".join(window): _contains_window(tokens, window)
                      for window in LICENSE_CONTRADICTIONS}
    urls: collections.Counter[str] = collections.Counter()
    index = 0
    while index < len(normalized):
        if normalized[index] not in URL_CHARS:
            index += 1; continue
        start = index
        while index < len(normalized) and normalized[index] in URL_CHARS:
            index += 1
        token = normalized[start:index]
        before = normalized[start - 1] if start else None
        after = normalized[index] if index < len(normalized) else None
        bounded = all(ch is None or unicodedata.category(ch)[0] not in {"L", "N"}
                      for ch in (before, after))
        if bounded and token in LICENSE_URLS:
            urls[token] += 1
    positive_count = sum(phrases.values()) + sum(urls.values())
    contradiction_count = sum(contradictions.values())
    return {"eligible": positive_count > 0 and contradiction_count == 0,
            "positive_occurrence_count": positive_count,
            "positive_phrase_counts": dict(sorted(phrases.items())),
            "positive_url_counts": dict(sorted(urls.items())),
            "contradiction_counts": dict(sorted(contradictions.items())),
            "contradiction_count": contradiction_count}


def _license() -> dict[str,Any]:
    lp=RAW/"LICENSE.txt"
    license_result=license_evidence(read_text_nofollow(lp))
    ok=license_result["eligible"]
    return {"schema_version":"msae_independent_source_v9_license_v1","license_id":"CC-BY-SA-4.0",
            "license_path":"LICENSE.txt","license_sha256":sha_file(lp),
            "license_url":"https://creativecommons.org/licenses/by-sa/4.0/",
            "evidence":{"LICENSE.txt":license_result},
            "obligations":["attribution","share_alike"],"raw_committed":False,"payload_committed":False,
            "contradiction_count":license_result["contradiction_count"],
            "status":"eligible" if ok else "ineligible"}


def _group_census_one(path: Path) -> tuple[dict[str, Any], set[str]]:
    marker_count=sentence_count=empty_count=orphan_count=duplicate_count=0
    premarker_sentence_count=0
    marker_seen=False; current: str | None=None; current_sentences=0; in_sentence=False
    groups: set[str]=set()
    def flush_sentence() -> None:
        nonlocal sentence_count,current_sentences,in_sentence,orphan_count,premarker_sentence_count
        if not in_sentence:return
        sentence_count+=1;current_sentences+=1
        if not marker_seen:premarker_sentence_count+=1
        elif current is None:orphan_count+=1
        in_sentence=False
    for line in read_text_nofollow(path).splitlines():
        if not line:
            flush_sentence();continue
        if line.startswith("# newdoc id = "):
            flush_sentence()
            if marker_seen and current_sentences==0:empty_count+=1
            value=canonical_group_id(line[len("# newdoc id = "):])
            if value in groups:duplicate_count+=1
            groups.add(value);marker_count+=1;marker_seen=True;current=value;current_sentences=0
        elif line.casefold().lstrip().startswith("# newdoc"):
            raise GateFailure("malformed_document_group_marker")
        elif not line.startswith("#"):
            in_sentence=True
    flush_sentence()
    if marker_seen and current_sentences==0:empty_count+=1
    if marker_seen:orphan_count+=premarker_sentence_count
    group_count=marker_count if marker_seen else sentence_count
    report={"marker_count":marker_count,"sentence_count":sentence_count,"group_count":group_count,
            "empty_group_count":empty_count,"orphan_sentence_count":orphan_count,
            "duplicate_group_count":duplicate_count,
            "group_id_set_sha256":sha_bytes(_canonical_ascii_bytes(
                sorted(sha_bytes(group_id.encode("utf-8")) for group_id in groups)))}
    return report,groups


def document_group_census() -> dict[str, Any]:
    files={};ids={};marker_count=0
    for partition,name in SOURCE_FILES.items():
        files[name],ids[partition]=_group_census_one(RAW/name)
        marker_count+=files[name]["marker_count"]
    intersection=set()
    names=tuple(ids)
    for index,left in enumerate(names):
        for right in names[index+1:]:intersection|=ids[left]&ids[right]
    bad=sum(item["empty_group_count"]+item["orphan_sentence_count"]+item["duplicate_group_count"]
            for item in files.values())
    policy="explicit_newdoc" if files[SOURCE_FILES["test"]]["marker_count"] else "sent_id_as_group"
    return {"schema_version":"msae_independent_source_v9_document_group_census_v1",
            "newdoc_marker_count":marker_count,"files":dict(sorted(files.items())),
            "test_group_policy":policy,"cross_partition_group_id_count":len(intersection),
            "natural_unit":"sentence","split_group_unit":"explicit_document_or_sent_id_fallback",
            "document_speaker_cluster_inference_authorized":False,
            "status":"eligible" if bad==0 and not intersection else "ineligible"}


def _source_family(inventory: dict[str,Any], raw_hashes:set[str]) -> dict[str,Any]:
    matches=[];whole=[];pathname_matches=[]
    def aliases(value: str) -> list[str]:
        tokens=tuple(LEX.findall(unicodedata.normalize("NFKC",value).casefold()))
        return [" ".join(sequence) for sequence in ALIAS_TOKEN_SEQUENCES
                if _contains_window(tokens,sequence)]
    def file_aliases(path: Path) -> list[str]:
        decoder=codecs.getincrementaldecoder("utf-8")("strict");tail="";found=set()
        fd=open_repo_file(path)
        try:
            before=os.fstat(fd)
            while True:
                payload=os.read(fd,1024*1024)
                final=not payload
                text=decoder.decode(payload,final=final)
                normalized=unicodedata.normalize("NFKC",text).casefold()
                found.update(aliases(tail+normalized));tail=normalized[-256:]
                if final:break
            after=os.fstat(fd)
            try:current=path.lstat()
            except OSError as error:raise GateFailure("file_mutated_while_reading") from error
            if (_stat_fingerprint(before)!=_stat_fingerprint(after)
                    or _stat_fingerprint(before)!=_stat_fingerprint(current)):
                raise GateFailure("file_mutated_while_reading")
        finally:os.close(fd)
        return sorted(found)
    for item in inventory["entries"]:
        rel=item["path"]
        if aliases(rel):
            pathname_matches.append(rel)
        if item.get("sha256") in raw_hashes:whole.append(rel)
        if item["disposition"] != "text_scanned":continue
        p=ROOT/rel
        found=file_aliases(p)
        if found:matches.append({"path":rel,"aliases":found})
    eligible=not matches and not pathname_matches and not whole
    return {"schema_version":"msae_independent_source_v9_source_family_v1","status":"eligible" if eligible else "ineligible",
            "disposition":"project_source_use_unseen_before_v9","content_occurrence_count":len(matches),
            "content_occurrences":matches,"pathname_occurrence_count":len(pathname_matches),
            "pathname_occurrences":sorted(pathname_matches),"whole_file_digest_matches":sorted(whole),
            "history_inputs_sha256":validate_history_registry_binding(inventory),
            "source_text_published":False}


PEDIGREE_URL = re.compile(rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{3,512}", re.I)
PEDIGREE_UD = re.compile(rb"(?<![A-Za-z0-9_])ud_[A-Za-z0-9_-]{2,128}(?![A-Za-z0-9_])", re.I)
PEDIGREE_KEYS = rb'(?:source_repo|source_url|repo_url|repository|url|source_revision|source_commit|commit|revision|dataset|dataset_id|dataset_name|source_name|source_id|corpus|treebank)'
PEDIGREE_JSON = re.compile(rb'"' + PEDIGREE_KEYS + rb'"\s{0,256}:\s{0,256}"([^"\\]{1,1024})"', re.I)
PEDIGREE_OVERBOUND = (re.compile(rb'"' + PEDIGREE_KEYS + rb'"\s{257}', re.I),
                       re.compile(rb'"' + PEDIGREE_KEYS + rb'"\s{0,256}:\s{257}', re.I))
PEDIGREE_URL_OVERLONG = re.compile(
    rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{513}", re.I)
PEDIGREE_UD_OVERLONG = re.compile(
    rb"(?<![A-Za-z0-9_])ud_[A-Za-z0-9_-]{129}", re.I)
PEDIGREE_JSON_PREFIX = re.compile(
    rb'"' + PEDIGREE_KEYS + rb'"\s{0,256}:\s{0,256}"', re.I)
PEDIGREE_CHUNK_BYTES = 1_048_576
PEDIGREE_OVERLAP_BYTES = 2_048
PEDIGREE_STRIP = " \t\r\n\"'`.,;:()[]{}<>"


def normalize_pedigree(raw: bytes) -> str:
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise GateFailure("invalid_candidate_pedigree_identifier") from error
    value = " ".join(unicodedata.normalize("NFKC", value).casefold().split()).strip(PEDIGREE_STRIP)
    if value.startswith("http://"):
        value = "https://" + value[7:]
    if value.endswith("/"):
        value = value[:-1]
    if value.endswith(".git"):
        value = value[:-4]
    if value.endswith("/"):
        value = value[:-1]
    if not value:
        raise GateFailure("empty_candidate_pedigree_identifier")
    return value


def pedigree_hash(value: str) -> str:
    return sha_bytes(b"msae-v9/pedigree\0" + value.encode("utf-8"))


def candidate_pedigree_identifiers(payload: bytes) -> set[str]:
    """Apply the frozen history-registry byte grammar with its exact chunk/carry policy."""
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise GateFailure("invalid_candidate_pedigree_identifier") from error

    # The accepted JSON regex deliberately excludes escapes.  Prospectively reject every
    # source-key construct that would otherwise be silently omitted as empty, escaped, or
    # longer than the 1,024-byte capture bound.
    for item in PEDIGREE_JSON_PREFIX.finditer(payload):
        end=payload.find(b'"',item.end())
        if end==item.end():
            raise GateFailure("empty_candidate_pedigree_identifier")
        if end<0 or end-item.end()>1024 or b"\\" in payload[item.end():end]:
            raise GateFailure("ambiguous_candidate_pedigree_syntax")

    identifiers: set[str] = set()
    pending: set[tuple[int,int]] = set()
    tail=b""
    for offset in range(0,len(payload),PEDIGREE_CHUNK_BYTES):
        block=payload[offset:offset+PEDIGREE_CHUNK_BYTES]
        combined=tail+block
        boundary=len(tail)
        base=offset-boundary
        final=offset+len(block)==len(payload)
        checks=tuple((pattern,"overbound_candidate_pedigree_whitespace")
                     for pattern in PEDIGREE_OVERBOUND)+(
            (PEDIGREE_URL_OVERLONG,"overlength_candidate_pedigree_identifier"),
            (PEDIGREE_UD_OVERLONG,"overlength_candidate_pedigree_identifier"),)
        for pattern,code in checks:
            if any(match.end()>boundary for match in pattern.finditer(combined)):
                raise GateFailure(code)
        for pattern_index,pattern in enumerate((PEDIGREE_URL,PEDIGREE_UD,PEDIGREE_JSON)):
            for match in pattern.finditer(combined):
                occurrence=(pattern_index,base+match.start())
                if match.end()<=boundary and occurrence not in pending:
                    # The complete occurrence was already visible in the preceding block.  This
                    # is also what prevents a new left-edge lookbehind boundary from inventing a
                    # UD token wholly inside the carried tail.
                    continue
                # A bounded token ending exactly at a non-final read boundary may continue in
                # the next block.  Mark only that exact pattern/start as pending, allowing it to
                # be emitted from the otherwise-skipped carried tail once the next byte is known.
                if not final and match.end()==len(combined):
                    pending.add(occurrence)
                    continue
                pending.discard(occurrence)
                identifiers.add(normalize_pedigree(
                    match.group(1) if pattern is PEDIGREE_JSON else match.group(0)))
        tail=combined[-PEDIGREE_OVERLAP_BYTES:]
    if pending:
        raise GateFailure("candidate_pedigree_chunk_state")
    return identifiers


def candidate_pedigree() -> dict[str, Any]:
    registry = strict_json(PROV / "historical_source_registry.json")
    historical = {item["identifier_sha256"] for item in registry["entries"]}
    allowed = {item["identifier_sha256"] for item in registry["allowed_framework_identifiers"]}
    identifiers = {normalize_pedigree(value.encode("utf-8")) for value in
                   (REPO, COMMIT, "UD_Swedish-Talbanken", "sv_talbanken", *SOURCE_FILES.values())}
    per_file: dict[str, list[str]] = {}
    for name in (*SOURCE_FILES.values(), "LICENSE.txt"):
        payload = read_bytes_nofollow(RAW/name)
        file_identifiers=candidate_pedigree_identifiers(payload)
        identifiers.update(file_identifiers)
        per_file[name]=sorted({pedigree_hash(value) for value in file_identifiers})
    hashes = sorted({pedigree_hash(value) for value in identifiers})
    blocking = sorted((set(hashes) & historical) - allowed)
    return {"schema_version": "msae_independent_source_v9_candidate_pedigree_v1",
            "registry_sha256": sha_file(PROV / "historical_source_registry.json"),
            "candidate_identifier_count": len(hashes), "candidate_identifier_sha256": hashes,
            "candidate_file_identifier_counts": {name:len(values) for name,values in per_file.items()},
            "candidate_file_identifier_sha256": per_file,
            "allowed_shared_identifier_sha256": sorted(set(hashes) & allowed),
            "blocking_identifier_sha256": blocking, "blocking_identifier_count": len(blocking),
            "source_prose_published": False, "status": "eligible" if not blocking else "ineligible"}


def _history_pedigree_scan(inputs: list[dict[str, Any]], domain: bytes
                           ) -> tuple[list[dict[str, Any]], int, dict[str, dict[str, Any]]]:
    """Rebuild the frozen byte-regex registry without retaining source text."""
    found: dict[str, dict[str, Any]] = {}
    overbound_count = 0
    patterns = (("url", PEDIGREE_URL), ("ud_token", PEDIGREE_UD),
                ("json_source_field", PEDIGREE_JSON))
    for record in inputs:
        path = ROOT / record["path"]
        fd = open_repo_file(path)
        try:
            opened = os.fstat(fd)
            if opened.st_size != record["size"]:
                raise GateFailure("history_registry_input_drift")
            digest = hashlib.sha256()
            tail = b""
            offset = 0
            pending: set[tuple[int, int]] = set()
            while True:
                block = os.read(fd, PEDIGREE_CHUNK_BYTES)
                if not block:
                    break
                digest.update(block)
                final = offset + len(block) == opened.st_size
                combined = tail + block
                absolute_base = offset - len(tail)
                boundary = len(tail)
                for pattern in PEDIGREE_OVERBOUND:
                    for match in pattern.finditer(combined):
                        if match.end() > boundary:
                            overbound_count += 1
                url_overlong = {absolute_base + match.start() for match in PEDIGREE_URL_OVERLONG.finditer(combined)}
                ud_overlong = {absolute_base + match.start() for match in PEDIGREE_UD_OVERLONG.finditer(combined)}
                for pattern_index, (kind, pattern) in enumerate(patterns):
                    for match in pattern.finditer(combined):
                        absolute_start = absolute_base + match.start()
                        occurrence = (pattern_index, absolute_start)
                        if match.end() <= boundary and occurrence not in pending:
                            continue
                        if not final and match.end() == len(combined):
                            pending.add(occurrence)
                            continue
                        pending.discard(occurrence)
                        if ((kind == "url" and absolute_start in url_overlong)
                                or (kind == "ud_token" and absolute_start in ud_overlong)):
                            continue
                        raw = match.group(1) if kind == "json_source_field" else match.group(0)
                        try:
                            normalized = normalize_pedigree(raw)
                        except (GateFailure, UnicodeError):
                            continue
                        item = found.setdefault(normalized, {"kinds": set(), "count": 0, "paths": set()})
                        item["kinds"].add(kind)
                        item["count"] += 1
                        item["paths"].add(record["path"])
                tail = combined[-PEDIGREE_OVERLAP_BYTES:]
                offset += len(block)
            if pending:
                raise GateFailure("history_registry_chunk_state")
            if digest.hexdigest() != record["sha256"]:
                raise GateFailure("history_registry_input_drift")
        finally:
            os.close(fd)
    entries = []
    for normalized, item in found.items():
        paths = sorted(item["paths"])
        entries.append({
            "identifier_sha256": sha_bytes(domain + normalized.encode("utf-8")),
            "kinds": sorted(item["kinds"]),
            "occurrence_count": item["count"],
            "path_count": len(paths),
            "paths_sha256": sha_bytes(_canonical_ascii_bytes(paths)),
        })
    return sorted(entries, key=lambda item: item["identifier_sha256"]), overbound_count, found


def build_registry() -> None:
    """Create v9 source-free history/alias artifacts from the exact pre-v8 input set."""
    registry_path = PROV / "historical_source_registry.json"
    screen_path = PROV / "preacquisition_alias_screen.json"
    if present_path(registry_path) or present_path(screen_path):
        raise GateFailure("registry_already_exists")
    verify_v8_carryover()
    verify_frozen_v9_authority_bindings()
    v8_registry_path = ROOT / "reports/provenance/msae_independent_source_v8/historical_source_registry.json"
    v8_registry = strict_json(v8_registry_path)
    inputs = v8_registry["inputs"]
    if (v8_registry.get("inputs_sha256") != sha_bytes(_canonical_ascii_bytes(inputs))
            or v8_registry.get("input_count") != len(inputs)):
        raise GateFailure("v8_registry_input_drift")
    v8_entries, overbound, normalized_found = _history_pedigree_scan(inputs, b"msae-v8/pedigree\0")
    if v8_entries != v8_registry["entries"] or overbound != v8_registry["overbound_json_source_key_construct_count"]:
        raise GateFailure("v8_registry_reconstruction_drift")
    entries = []
    for normalized, item in normalized_found.items():
        paths = sorted(item["paths"])
        entries.append({"identifier_sha256": sha_bytes(b"msae-v9/pedigree\0" + normalized.encode("utf-8")),
                        "kinds": sorted(item["kinds"]), "occurrence_count": item["count"],
                        "path_count": len(paths), "paths_sha256": sha_bytes(_canonical_ascii_bytes(paths))})
    entries.sort(key=lambda item: item["identifier_sha256"])
    v9_overbound = overbound
    registry = dict(v8_registry)
    registry.update(
        schema_version="msae_independent_source_v9_historical_source_registry_v1",
        domain_utf8="msae-v9/pedigree",
        input_policy=("exact pre-v8 text history; exact v9 authority and enumerated v8 candidate-control "
                      "carryover excluded; exact v8 data universe opaque; Atlas quarantines lstat-only"),
        entries=entries,
        identifier_count=len(entries),
        overbound_json_source_key_construct_count=v9_overbound,
    )
    registry["allowed_framework_identifiers"] = [
        {"normalized_identifier": item["normalized_identifier"],
         "identifier_sha256": sha_bytes(b"msae-v9/pedigree\0" + item["normalized_identifier"].encode("utf-8"))}
        for item in v8_registry["allowed_framework_identifiers"]
    ]
    registry["normalization_goldens"] = [
        {**item, "identifier_sha256": sha_bytes(b"msae-v9/pedigree\0" + item["normalized"].encode("utf-8"))}
        for item in v8_registry["normalization_goldens"]
    ]
    write_json(registry_path, registry)
    v8_screen = strict_json(ROOT / "reports/provenance/msae_independent_source_v8/preacquisition_alias_screen.json")
    carryover = strict_json(ROOT / CARRYOVER_PATH)
    screen = dict(v8_screen)
    screen.update(
        schema_version="msae_independent_source_v9_preacquisition_alias_screen_v2",
        history_registry_path="reports/provenance/msae_independent_source_v9/historical_source_registry.json",
        history_registry_sha256=sha_file(registry_path),
        metadata_discovery={"method": "retained_v8_public_metadata_only", "network_operations": 0,
                            "source_blobs_acquired": False, "source_content_read": False},
        v8_candidate_control_carryover_authority_sha256=CARRYOVER_SHA256,
        v8_candidate_control_carryover_files=[
            {"path": item["path"], "sha256": item["sha256"]}
            for item in carryover["v8_control_files"]
        ],
        v8_candidate_control_carryover_count=17,
    )
    write_json(screen_path, screen)


def verify_frozen_v9_authority_bindings() -> dict[str, str]:
    if any(sha_file(ROOT/path)!=digest for path,digest in V9_FROZEN_AUTHORITY_SHA256.items()):
        raise GateFailure("predecessor_drift")
    return dict(V9_FROZEN_AUTHORITY_SHA256)


def validate_acquisition_exit_statuses(statuses: Any, names: list[str]) -> None:
    expected={"ignore_raw":0,"ignore_private":0,"clone":0,"checkout":0,"head":0,"tree":0,
              "ls_tree":0,"hash_object_count":len(names)}
    if statuses!=expected:
        raise GateFailure("source_acquisition_exit_status")


def _verify_predecessor_and_raw(*, read_raw: bool = True) -> dict[str, Any]:
    expected = {ROOT/path:digest for path,digest in verify_frozen_v9_authority_bindings().items()}
    expected.update({ROOT/path:digest for path,digest in _predecessor_hashes().items()})
    if any(sha_file(path) != digest for path,digest in expected.items()):
        raise GateFailure("predecessor_drift")
    required_public=(
        PROV/"baseline_inventory.json",
        PROV/"preacquisition_authority_manifest.json",
        ROOT/"reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md",
        PROV/"source_acquisition_entry.json",
        PROV/"source_acquisition.json",
    )
    for path in required_public:
        regular_state_nofollow(path,mode=0o644,nlink=1)
    authority = verify_authority_chain()
    entry=strict_json(PROV/"source_acquisition_entry.json")
    acquisition=strict_json(PROV/"source_acquisition.json")
    exact_keys(entry,{"schema_version","status","authority_manifest_sha256","authority_review_sha256",
        "baseline_inventory_sha256","config_sha256","runner_sha256","source_repo","source_commit","files",
        "subprocesses_started","model_scoring_authorized","k2_or_branch_training_authorized",
        "stage_c_authorized"},"source_acquisition_entry_drift")
    exact_keys(acquisition,{"schema_version","source_repo","source_commit","resolved_head","tree_object_sha1",
        "tree_verified_from_ls_tree","tree_paths","tree_blob_sha1","files","authority_manifest_sha256",
        "authority_review_sha256","source_acquisition_entry_sha256","acquisition_gate_argument","config_sha256",
        "runner_sha256","executed_clone_argv","executed_checkout_argv","environment","clone_dir","empty_home",
        "proxy_variables_present","ignore_checks","commands","sparse_checkout_sha256","raw_directory",
        "command_exit_status","head_stdout_sha256","head_stderr_sha256","tree_stdout_sha256","tree_stderr_sha256",
        "ls_tree_stdout_sha256","ls_tree_stderr_sha256","clone_stdout_sha256","clone_stderr_sha256",
        "checkout_stdout_sha256","checkout_stderr_sha256","source_content_printed","network_access",
        "model_operations","gpu_queries","training_runs"},"source_acquisition_drift")
    names=[*SOURCE_FILES.values(),"LICENSE.txt"]
    config=validate_acquisition_config(ROOT/"configs/msae_independent_source_v9/acquisition.json")
    environment=acquisition.get("environment",{})
    clone_dir=acquisition.get("clone_dir")
    empty_home=acquisition.get("empty_home")
    expected_clone=[clone_dir if item=="${CLONE_DIR}" else item for item in config["clone_argv"]]
    expected_checkout=[clone_dir if item=="${CLONE_DIR}" else item for item in config["checkout_argv"]]
    expected_environment={key:(empty_home if value=="${EMPTY_HOME}" else value) for key,value in config["environment"].items()}
    if (entry.get("schema_version")!="msae_independent_source_v9_source_acquisition_entry_v1"
            or entry.get("status")!="entered"
            or entry.get("authority_manifest_sha256")!=sha_file(PROV/"preacquisition_authority_manifest.json")
            or entry.get("authority_review_sha256")!=authority["authority_review_sha256"]
            or entry.get("baseline_inventory_sha256")!=sha_file(PROV/"baseline_inventory.json")
            or entry.get("config_sha256")!=sha_file(ROOT/"configs/msae_independent_source_v9/acquisition.json")
            or entry.get("runner_sha256")!=sha_file(ROOT/"scripts/acquire_msae_independent_source_v9.py")
            or entry.get("source_repo")!=REPO or entry.get("source_commit")!=COMMIT or entry.get("files")!=names
            or entry.get("subprocesses_started")!=0
            or entry.get("model_scoring_authorized") is not False
            or entry.get("k2_or_branch_training_authorized") is not False
            or entry.get("stage_c_authorized") is not False):
        raise GateFailure("source_acquisition_entry_drift")
    if (acquisition.get("schema_version")!="msae_independent_source_v9_source_acquisition_v1"
            or acquisition.get("source_repo") != REPO or acquisition.get("source_commit") != COMMIT
            or acquisition.get("resolved_head") != COMMIT
            or not re.fullmatch(r"[0-9a-f]{40}",str(acquisition.get("tree_object_sha1","")))
            or acquisition.get("tree_verified_from_ls_tree") is not True
            or acquisition.get("authority_manifest_sha256") != sha_file(PROV/"preacquisition_authority_manifest.json")
            or acquisition.get("authority_review_sha256") != authority["authority_review_sha256"]
            or acquisition.get("source_acquisition_entry_sha256") != sha_file(PROV/"source_acquisition_entry.json")
            or acquisition.get("acquisition_gate_argument") != authority["authority_review_sha256"]
            or acquisition.get("config_sha256") != sha_file(ROOT/"configs/msae_independent_source_v9/acquisition.json")
            or acquisition.get("executed_clone_argv") != expected_clone
            or acquisition.get("executed_checkout_argv") != expected_checkout
            or environment != expected_environment or acquisition.get("proxy_variables_present") != []
            or acquisition.get("sparse_checkout_sha256") != sha_bytes(("\n".join("/"+name for name in names)+"\n").encode("utf-8"))
            or acquisition.get("tree_paths") != names
            or acquisition.get("runner_sha256") != sha_file(ROOT/"scripts/acquire_msae_independent_source_v9.py")
            or acquisition.get("source_content_printed") is not False
            or acquisition.get("network_access") != "git_clone_and_checkout_only"
            or acquisition.get("model_operations") != 0 or acquisition.get("gpu_queries") != 0
            or acquisition.get("training_runs") != 0
            or set(acquisition.get("files",{})) != set(names)):
        raise GateFailure("source_acquisition_drift")
    statuses=acquisition.get("command_exit_status",{})
    validate_acquisition_exit_statuses(statuses,names)
    commands=acquisition.get("commands",[])
    expected_command_names=["ignore_raw","ignore_private","clone","checkout","head","tree","ls_tree",*["hash_object:"+name for name in names]]
    expected_command_argv=[
        [*config["ignore_argv"][:-1],"data/msae_independent_source_v9/raw/sentinel"],
        [*config["ignore_argv"][:-1],"data/msae_independent_source_v9/private/sentinel"],
        expected_clone,expected_checkout,
        [clone_dir if item=="${CLONE_DIR}" else item for item in config["head_argv"]],
        [clone_dir if item=="${CLONE_DIR}" else COMMIT+"^{tree}" if item=="${SOURCE_COMMIT}^{tree}" else item for item in config["tree_argv"]],
        [clone_dir if item=="${CLONE_DIR}" else COMMIT if item=="${SOURCE_COMMIT}" else item for item in config["ls_tree_argv"]],
        *[[clone_dir if item=="${CLONE_DIR}" else name if item=="${CHECKED_OUT_FILE}" else item
           for item in config["hash_object_argv"]] for name in names],
    ]
    if ([item.get("name") for item in commands]!=expected_command_names
            or any(set(item)!={"name","argv","exit_status","stdout_bytes","stdout_sha256","stderr_bytes","stderr_sha256"}
                   or item.get("argv")!=expected_command_argv[index]
                   or item.get("exit_status")!=0 or not _is_count(item.get("stdout_bytes"))
                   or not _is_count(item.get("stderr_bytes"))
                   or not re.fullmatch(r"[0-9a-f]{64}",str(item.get("stdout_sha256","")))
                   or not re.fullmatch(r"[0-9a-f]{64}",str(item.get("stderr_sha256","")))
                   for index,item in enumerate(commands))):
        raise GateFailure("source_acquisition_command_evidence")
    by_command={item["name"]:item for item in commands}
    ignores=acquisition.get("ignore_checks",[])
    if ([item.get("path") for item in ignores] != ["data/msae_independent_source_v9/raw/sentinel","data/msae_independent_source_v9/private/sentinel"]
            or any(set(item)!={"path","stdout_sha256","stderr_sha256","exit_status"}
                   or item.get("exit_status")!=0 or not re.fullmatch(r"[0-9a-f]{64}",str(item.get("stdout_sha256","")))
                   or not re.fullmatch(r"[0-9a-f]{64}",str(item.get("stderr_sha256",""))) for item in ignores)):
        raise GateFailure("source_ignore_evidence")
    if any(ignores[index][field]!=by_command[name][field] for index,name in enumerate(("ignore_raw","ignore_private"))
           for field in ("stdout_sha256","stderr_sha256","exit_status")):
        raise GateFailure("source_ignore_evidence_binding")
    for field in ("clone_stdout_sha256","clone_stderr_sha256","checkout_stdout_sha256","checkout_stderr_sha256"):
        if acquisition.get(field) != sha_bytes(b""):
            raise GateFailure("source_acquisition_output")
    direct={
        "clone_stdout_sha256":by_command["clone"]["stdout_sha256"],"clone_stderr_sha256":by_command["clone"]["stderr_sha256"],
        "checkout_stdout_sha256":by_command["checkout"]["stdout_sha256"],"checkout_stderr_sha256":by_command["checkout"]["stderr_sha256"],
        "head_stdout_sha256":by_command["head"]["stdout_sha256"],"head_stderr_sha256":by_command["head"]["stderr_sha256"],
        "tree_stdout_sha256":by_command["tree"]["stdout_sha256"],"tree_stderr_sha256":by_command["tree"]["stderr_sha256"],
        "ls_tree_stdout_sha256":by_command["ls_tree"]["stdout_sha256"],"ls_tree_stderr_sha256":by_command["ls_tree"]["stderr_sha256"],
    }
    if any(acquisition.get(key)!=value for key,value in direct.items()):raise GateFailure("source_acquisition_output_binding")
    if any(by_command[name][field]!=expected for name in ("clone","checkout")
           for field,expected in (("stdout_bytes",0),("stderr_bytes",0),("stdout_sha256",sha_bytes(b"")),("stderr_sha256",sha_bytes(b"")))):
        raise GateFailure("source_acquisition_output_reconstruction")
    blobs=acquisition.get("tree_blob_sha1",{})
    expected_ls=b"".join(f"100644 blob {blobs[name]}\t{name}\0".encode() for name in sorted(names))
    if (by_command["head"]["stdout_bytes"]!=41 or by_command["head"]["stdout_sha256"]!=sha_bytes((COMMIT+"\n").encode())
            or by_command["head"]["stderr_bytes"]!=0 or by_command["head"]["stderr_sha256"]!=sha_bytes(b"")
            or by_command["tree"]["stdout_bytes"]!=41
            or by_command["tree"]["stdout_sha256"]!=sha_bytes((acquisition["tree_object_sha1"]+"\n").encode())
            or by_command["tree"]["stderr_bytes"]!=0 or by_command["tree"]["stderr_sha256"]!=sha_bytes(b"")
            or by_command["ls_tree"]["stdout_bytes"]!=len(expected_ls)
            or by_command["ls_tree"]["stdout_sha256"]!=sha_bytes(expected_ls) or by_command["ls_tree"]["stderr_bytes"]!=0
            or by_command["ls_tree"]["stderr_sha256"]!=sha_bytes(b"")):
        raise GateFailure("source_acquisition_output_reconstruction")
    for name in names:
        record=by_command["hash_object:"+name];expected=(blobs[name]+"\n").encode()
        if (record["stdout_bytes"]!=len(expected) or record["stdout_sha256"]!=sha_bytes(expected)
                or record["stderr_bytes"]!=0 or record["stderr_sha256"]!=sha_bytes(b"")):
            raise GateFailure("source_acquisition_blob_output")
    if not read_raw:
        # The expected raw hashes are authority-bound above; current raw bytes are
        # intentionally not opened until the durable scientific marker exists.
        return acquisition
    raw_fd=open_repo_dir(RAW)
    try:raw_stat=os.fstat(raw_fd);raw_names=sorted(os.listdir(raw_fd))
    finally:os.close(raw_fd)
    if stat.S_IMODE(raw_stat.st_mode)!=0o555:raise GateFailure("raw_directory_drift")
    raw_record=acquisition.get("raw_directory",{})
    if (set(raw_record)!={"device","inode","mode","nlink"} or set(acquisition.get("tree_blob_sha1",{}))!=set(names)
            or {key:raw_record.get(key) for key in ("device","inode","mode","nlink")}
            != {"device":raw_stat.st_dev,"inode":raw_stat.st_ino,"mode":stat.S_IMODE(raw_stat.st_mode),"nlink":raw_stat.st_nlink}):
        raise GateFailure("raw_directory_identity_drift")
    if raw_names != sorted(names):
        raise GateFailure("raw_file_set_drift")
    for name in names:
        item=acquisition["files"][name]
        exact_keys(item,{"sha256","size","git_blob_sha1","mode","nlink"},"raw_binding_drift")
        if (item.get("git_blob_sha1")!=acquisition.get("tree_blob_sha1",{}).get(name)
                or not re.fullmatch(r"[0-9a-f]{40}",str(item.get("git_blob_sha1","")))):
            raise GateFailure("source_tree_blob_drift")
        path=RAW/name; st=regular_state_nofollow(path)
        if (stat.S_IMODE(st.st_mode)!=0o444
                or st.st_nlink!=1 or st.st_size!=item["size"] or sha_file(path)!=item["sha256"]
                or item.get("mode")!=0o444 or item.get("nlink")!=1
                or git_blob_sha1(path)!=item["git_blob_sha1"]):
            raise GateFailure("raw_binding_drift")
    return acquisition


def _verify_history_snapshot(inventory: dict[str, Any], allowed_added: set[str] | None = None,
                             allowed_prefixes: tuple[str,...] = ()) -> None:
    baseline_paths={item["path"] for item in inventory["entries"]}
    current_paths={rel for _path,rel in _walk_paths_allow_v9(include_v9=True)}
    additions=current_paths-baseline_paths
    allowed_added=allowed_added or set()
    unexpected={rel for rel in additions if rel not in allowed_added and not any(rel.startswith(prefix) for prefix in allowed_prefixes)}
    if unexpected:
        raise GateFailure("history_structural_addition")
    for item in inventory["entries"]:
        if item["disposition"] not in {"text_scanned", "archive_scanned", "binary_unscanned", "v9_authority",
                                      "v8_candidate_control_carryover", "quarantine"}:
            raise GateFailure("history_baseline_schema")
        path=ROOT/item["path"]
        if item["disposition"]=="quarantine":
            s=path.lstat();digest=None;is_text=False
        else:
            fd=open_repo_file(path)
            try:
                s=os.fstat(fd);digest,is_text=_hash_and_text_fd(fd);after=os.fstat(fd)
                current=path.lstat()
            finally:os.close(fd)
            if _stat_fingerprint(s)!=_stat_fingerprint(after) or _stat_fingerprint(s)!=_stat_fingerprint(current):
                raise GateFailure("history_snapshot_drift")
        if (not stat.S_ISREG(s.st_mode) or s.st_size!=item["size"] or s.st_dev!=item["device"]
                or s.st_ino!=item["inode"] or s.st_mtime_ns!=item["mtime_ns"]
                or stat.S_IMODE(s.st_mode)!=item["mode"] or s.st_nlink!=item["nlink"]):
            raise GateFailure("history_snapshot_drift")
        if digest != item["sha256"]:
            raise GateFailure("history_snapshot_hash_drift")
        if item["disposition"] == "binary_unscanned" and is_text:
            raise GateFailure("binary_history_classification_drift")


def _raw_history_additions() -> set[str]:
    return {f"data/msae_independent_source_v9/raw/{COMMIT}/{name}"
            for name in [*SOURCE_FILES.values(),"LICENSE.txt"]}


def _control_history_additions(*, success: bool = False) -> set[str]:
    additions={
        "reports/provenance/msae_independent_source_v9/baseline_inventory.json",
        "reports/provenance/msae_independent_source_v9/preacquisition_authority_manifest.json",
        "reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md",
        "reports/provenance/msae_independent_source_v9/source_acquisition_entry.json",
    }
    if success:additions.add("reports/provenance/msae_independent_source_v9/source_acquisition.json")
    else:
        for name in ("source_acquisition.json","source_acquisition_rejection.json"):
            if present_path(PROV/name):additions.add(f"reports/provenance/msae_independent_source_v9/{name}")
    return additions


def _success_history_additions() -> set[str]:
    return (_control_history_additions(success=True)|_raw_history_additions()|
            {f"reports/provenance/msae_independent_source_v9/{name}"
             for name in SCIENTIFIC_ARTIFACT_NAMES}|
            {"data/msae_independent_source_v9/private/blind_payload.jsonl"})


def _rejection_history_additions(public_inventory: dict[str,Any],
                                  private_state: list[dict[str,Any]]) -> set[str]:
    additions=_control_history_additions()|_raw_history_additions()|{
        "reports/provenance/msae_independent_source_v9/rejection.json"}
    for item in [*public_inventory.get("entries",[]),*private_state]:
        if isinstance(item,dict) and item.get("state")=="present" and isinstance(item.get("path"),str):
            additions.add(item["path"])
    return additions


def verify_pre_payload_v9_namespace() -> None:
    fds=[]
    try:
        v9fd=open_repo_dir(RAW.parent.parent);fds.append(v9fd)
        rawrootfd=os.open("raw",os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0),dir_fd=v9fd);fds.append(rawrootfd)
        commitfd=os.open(COMMIT,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0),dir_fd=rawrootfd);fds.append(commitfd)
        for fd,mode in ((v9fd,0o700),(rawrootfd,0o700),(commitfd,0o555)):
            if stat.S_IMODE(os.fstat(fd).st_mode)!=mode:raise GateFailure("v9_namespace_directory_drift")
        if sorted(os.listdir(v9fd)) != ["raw"]:raise GateFailure("v9_namespace_extra_path")
        if sorted(os.listdir(rawrootfd)) != [COMMIT]:raise GateFailure("v9_raw_parent_extra_path")
        expected=sorted([*SOURCE_FILES.values(),"LICENSE.txt"])
        if sorted(os.listdir(commitfd)) != expected:raise GateFailure("raw_file_set_drift")
        for name in expected:
            s=os.stat(name,dir_fd=commitfd,follow_symlinks=False)
            if (not stat.S_ISREG(s.st_mode) or stat.S_IMODE(s.st_mode)!=0o444 or s.st_nlink!=1):
                raise GateFailure("raw_namespace_file_drift")
    finally:
        for fd in reversed(fds):os.close(fd)


def validate_static_contract(path: Path) -> list[str]:
    tree=ast.parse(read_text_nofollow(path));bad=[]
    forbidden_imports={"torch","transformers","jax","tensorflow","socket","subprocess","requests","urllib","http","ftplib","ctypes","importlib","asyncio"}
    forbidden_os={"system","popen","fork","forkpty","posix_spawn","posix_spawnp"}
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[x.name.split('.')[0] for x in node.names] if isinstance(node,ast.Import) else [(node.module or '').split('.')[0]]
            for name in names:
                if name in forbidden_imports:bad.append("forbidden_import:"+name)
            if isinstance(node,ast.Import):
                for name in node.names:
                    if name.name=="os" and name.asname is not None:bad.append("aliased_os_import")
            if isinstance(node,ast.ImportFrom) and node.module=="os":
                for name in node.names:
                    if name.name in forbidden_os or name.name.startswith(("spawn","exec")):
                        bad.append("forbidden_os_import:"+name.name)
                    if name.name=="*":bad.append("forbidden_os_import:*")
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {"eval","exec","__import__"}:bad.append("dynamic_call:"+node.func.id)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=="os":
            if node.func.attr in forbidden_os or node.func.attr.startswith(("spawn", "exec")):
                bad.append("forbidden_os_call:"+node.func.attr)
        if (isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="getattr"
                and len(node.args)>=2 and isinstance(node.args[0],ast.Name) and node.args[0].id=="os"
                and isinstance(node.args[1],ast.Constant) and isinstance(node.args[1].value,str)
                and (node.args[1].value in forbidden_os or node.args[1].value.startswith(("spawn","exec")))):
            bad.append("indirect_forbidden_os_call:"+node.args[1].value)
    return sorted(bad)


def process_snapshot() -> dict[str, Any]:
    forbidden=tuple(item.encode() for item in FORBIDDEN_PROCESS_TOKENS)
    entries=[]; matches=[]
    for child in sorted(Path("/proc").iterdir(), key=lambda item: int(item.name) if item.name.isdigit() else -1):
        if not child.name.isdigit():
            continue
        try:
            raw=(child/"cmdline").read_bytes()
            stat_text=(child/"stat").read_text()
            # The parenthesized comm field may itself contain whitespace.
            stat_fields=stat_text[stat_text.rfind(")") + 2:].split()
            exe=Path(os.readlink(child/"exe")).name
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
        codes=sorted(token.decode() for token in forbidden if token in raw.lower())
        item={"pid":int(child.name),"start_ticks":stat_fields[19],"executable_basename":exe,
              "command_sha256":sha_bytes(b"msae-v9/process\0"+raw),"forbidden_codes":codes}
        entries.append(item)
        if codes:matches.append(item)
    return {"schema_version":"msae_independent_source_v9_process_snapshot_v1",
            "observation_scope":"point_in_time_proc_snapshot","forbidden_tokens":[x.decode() for x in forbidden],
            "process_count":len(entries),"entries":entries,"forbidden_identity_count":len(matches),
            "status":"eligible" if not matches else "ineligible"}


def _training_entries(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    out=[]
    for item in inventory["entries"]:
        rel=item["path"].casefold();name=Path(rel).name
        if (rel.startswith("results/") or "checkpoint" in rel or name=="train_metrics.jsonl"
                or (rel.startswith("pilot_runs/") and Path(rel).suffix in {".pt",".pth",".ckpt",".safetensors"})):
            out.append({key:item.get(key) for key in ("path","size","mode","inode","mtime_ns","sha256","disposition")})
    return sorted(out,key=lambda item:item["path"])


def verify_training_roots(inventory: dict[str, Any]) -> None:
    recensus = _training_recensus(inventory)
    if recensus["status"] == "boundary_failure":
        raise GateFailure(recensus["failure_code"])
    if recensus["status"] != "eligible":
        raise GateFailure("training_root_delta")


def _walk_paths_allow_v9(include_v9: bool = False) -> Iterator[tuple[Path,str]]:
    yield from _walk_descriptor_paths(include_v9=include_v9,reject_v9_namespace=False)


def _authority_inputs() -> dict[str, str]:
    paths = [
        "docs/plan-msae-independent-source-v9.md",
        "reports/adversarial/msae_independent_source_v9_plan_review.md",
        CARRYOVER_PATH,
        "reports/provenance/msae_independent_source_v9/preacquisition_alias_screen.json",
        "reports/provenance/msae_independent_source_v9/historical_source_registry.json",
        "scripts/prepare_msae_independent_source_v9.py",
        "scripts/acquire_msae_independent_source_v9.py",
        "tests/test_prepare_msae_independent_source_v9.py",
        "configs/msae_independent_source_v9/acquisition.json",
        "reports/verification/msae_independent_source_v9_source_free_checks.log",
        "reports/adversarial/msae_independent_source_v9_preacquisition_implementation_review.md",
    ]
    return {path:sha_file(ROOT/path) for path in paths}


def implementation_review_sha() -> str:
    review=ROOT/"reports/adversarial/msae_independent_source_v9_preacquisition_implementation_review.md"
    required=[
        sha_file(ROOT/"docs/plan-msae-independent-source-v9.md"),
        sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_plan_review.md"),
        sha_file(ROOT/CARRYOVER_PATH),
        sha_file(PROV/"preacquisition_alias_screen.json"),
        sha_file(PROV/"historical_source_registry.json"),
        sha_file(Path(__file__)),
        sha_file(ROOT/"scripts/acquire_msae_independent_source_v9.py"),
        sha_file(ROOT/"tests/test_prepare_msae_independent_source_v9.py"),
        sha_file(ROOT/"configs/msae_independent_source_v9/acquisition.json"),
        sha_file(ROOT/"reports/verification/msae_independent_source_v9_source_free_checks.log"),
    ]
    return _require_ship_review(review,required)


def build_authority_manifest() -> None:
    path=PROV/"preacquisition_authority_manifest.json"
    if present_path(path):
        raise GateFailure("authority_manifest_already_exists")
    authority_review=ROOT/"reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md"
    if present_path(authority_review):
        raise GateFailure("authority_review_preexists_manifest")
    baseline=strict_json(PROV/"baseline_inventory.json")
    _verify_history_snapshot(
        baseline,
        allowed_added={"reports/provenance/msae_independent_source_v9/baseline_inventory.json"},
    )
    validate_history_registry_binding(baseline)
    verify_training_roots(baseline)
    implementation_review_sha();inputs=_authority_inputs()
    review_path=ROOT/"reports/adversarial/msae_independent_source_v9_preacquisition_implementation_review.md"
    _require_ship_review(review_path,[inputs["scripts/prepare_msae_independent_source_v9.py"],
                                      inputs["tests/test_prepare_msae_independent_source_v9.py"],
                                      inputs["configs/msae_independent_source_v9/acquisition.json"],
                                      inputs["reports/verification/msae_independent_source_v9_source_free_checks.log"]])
    snap=baseline["process_snapshot"]
    if snap.get("status")!="eligible" or snap.get("forbidden_identity_count")!=0:
        raise GateFailure("baseline_process_ineligible")
    value={"schema_version":"msae_independent_source_v9_preacquisition_authority_v1",
           "status":"approved_for_exact_source_acquisition","artifact_sha256":inputs,
           "predecessor_sha256":_predecessor_hashes(),
           "baseline_inventory_sha256":sha_file(PROV/"baseline_inventory.json"),
           "baseline_entries_sha256":baseline["entries_sha256"],
           "history_inputs_sha256":validate_history_registry_binding(baseline),
           "baseline_process_snapshot_sha256":sha_bytes(canonical_bytes(snap)),
           "baseline_forbidden_identity_count":0,
           "training_root_entries_sha256":baseline["training_root_entries_sha256"],
           "quarantine_content_reads":baseline["quarantine_content_reads"],
           "authority_review_required":True,"source_acquisition_authorized":True,
           "model_scoring_authorized":False,"k2_or_branch_training_authorized":False,
           "model_operations_initiated":0,"gpu_queries_initiated":0,"training_runs_initiated":0}
    write_json(path,value)


def verify_authority_chain() -> dict[str, Any]:
    manifest_path=PROV/"preacquisition_authority_manifest.json"
    manifest=strict_json(manifest_path)
    baseline=strict_json(PROV/"baseline_inventory.json")
    validate_history_registry_binding(baseline)
    expected_inputs=_authority_inputs()
    exact_keys(manifest,{"schema_version","status","artifact_sha256","predecessor_sha256",
        "baseline_inventory_sha256","baseline_entries_sha256","history_inputs_sha256","baseline_process_snapshot_sha256",
        "baseline_forbidden_identity_count","training_root_entries_sha256","quarantine_content_reads",
        "authority_review_required","source_acquisition_authorized","model_scoring_authorized",
        "k2_or_branch_training_authorized","model_operations_initiated","gpu_queries_initiated",
        "training_runs_initiated"},"authority_manifest_drift")
    if (manifest.get("schema_version")!="msae_independent_source_v9_preacquisition_authority_v1"
            or manifest.get("status")!="approved_for_exact_source_acquisition"
            or manifest.get("artifact_sha256")!=expected_inputs
            or manifest.get("predecessor_sha256")!=_predecessor_hashes()
            or manifest.get("baseline_inventory_sha256")!=sha_file(PROV/"baseline_inventory.json")
            or manifest.get("baseline_entries_sha256")!=baseline.get("entries_sha256")
            or manifest.get("history_inputs_sha256")!=validate_history_registry_binding(baseline)
            or manifest.get("baseline_process_snapshot_sha256")!=sha_bytes(canonical_bytes(baseline.get("process_snapshot")))
            or manifest.get("baseline_forbidden_identity_count")!=0
            or manifest.get("training_root_entries_sha256")!=baseline.get("training_root_entries_sha256")
            or manifest.get("quarantine_content_reads")!=0
            or manifest.get("authority_review_required") is not True
            or manifest.get("source_acquisition_authorized") is not True
            or manifest.get("model_scoring_authorized") is not False
            or manifest.get("k2_or_branch_training_authorized") is not False
            or manifest.get("model_operations_initiated")!=0 or manifest.get("gpu_queries_initiated")!=0
            or manifest.get("training_runs_initiated")!=0):
        raise GateFailure("authority_manifest_drift")
    review_path=ROOT/"reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md"
    review_sha=_require_ship_review(review_path,[sha_file(manifest_path),sha_file(PROV/"baseline_inventory.json")])
    return {**manifest,"authority_review_sha256":review_sha}


def build_baseline() -> None:
    if sys.version_info[:3] != (3,12,3) or unicodedata.unidata_version != "15.0.0":raise GateFailure("runtime_drift")
    if validate_static_contract(Path(__file__)):
        raise GateFailure("static_contract")
    validate_acquisition_config(ROOT/"configs/msae_independent_source_v9/acquisition.json")
    implementation_review_sha()
    inv=inventory_repository()
    inv["history_inputs_sha256"]=validate_history_registry_binding(inv)
    inv["process_snapshot"]=process_snapshot()
    if inv["process_snapshot"]["status"]!="eligible":raise GateFailure("forbidden_baseline_process")
    inv["training_root_entries"]=_training_entries(inv)
    inv["training_root_entries_sha256"]=sha_bytes(canonical_bytes(inv["training_root_entries"]))
    write_json(PROV/"baseline_inventory.json",inv)


def require_frozen_runtime() -> None:
    if sys.version_info[:3] != (3,12,3) or unicodedata.unidata_version != "15.0.0":
        raise GateFailure("runtime_drift")


def _eligible_history_recensus(inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "msae_independent_source_v9_history_recensus_v1",
        "status": "eligible", "failure_code": None,
        "expected_entries_sha256": inventory["entries_sha256"],
        "observed_entries_sha256": inventory["entries_sha256"],
        "expected_history_inputs_sha256": inventory["history_inputs_sha256"],
        "observed_history_inputs_sha256": inventory["history_inputs_sha256"],
        "added_paths": [], "removed_paths": [], "changed_paths": [],
        "quarantine_content_reads": 0,
    }


def _eligible_training_recensus(inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "msae_independent_source_v9_training_recensus_v1",
        "status": "eligible", "failure_code": None,
        "expected_entries_sha256": inventory["training_root_entries_sha256"],
        "observed_entries_sha256": inventory["training_root_entries_sha256"],
        "expected_entry_count": len(inventory["training_root_entries"]),
        "observed_entry_count": len(inventory["training_root_entries"]),
    }


def _history_recensus(inventory: dict[str, Any], allowed_added: set[str]) -> dict[str, Any]:
    """Reconstruct the frozen baseline without admitting generated files to history.

    The observed digests cover only the baseline entry universe.  Permitted protocol
    additions are checked structurally elsewhere and are deliberately not promoted
    into the historical-source input set.
    """
    expected_entries = inventory["entries"]
    expected_by_path = {item["path"]: item for item in expected_entries}
    expected_paths = set(expected_by_path)
    observed_entries: list[dict[str, Any]] = []
    observed_inputs: list[dict[str, Any]] = []
    removed: list[str] = []
    changed: list[str] = []
    try:
        current_paths = {rel for _path, rel in _walk_paths_allow_v9(include_v9=True)}
        added = sorted(current_paths - expected_paths - allowed_added)
        for item in expected_entries:
            rel = item["path"]
            path = ROOT / rel
            if rel not in current_paths:
                removed.append(rel)
                observed_entries.append({"path": rel, "state": "absent"})
                if item["disposition"] == "text_scanned":
                    observed_inputs.append({"path": rel, "sha256": None, "size": None})
                continue
            before = path.lstat()
            if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
                changed.append(rel)
                observed_entries.append({"path": rel, "state": "nonregular",
                                         "mode": stat.S_IMODE(before.st_mode),
                                         "size": before.st_size, "nlink": before.st_nlink})
                if item["disposition"] == "text_scanned":
                    observed_inputs.append({"path": rel, "sha256": None,
                                            "size": before.st_size})
                continue
            if item["disposition"] == "quarantine":
                digest = None
                is_text = False
                after = path.lstat()
            else:
                fd = open_repo_file(path)
                try:
                    opened = os.fstat(fd)
                    digest, is_text = _hash_and_text_fd(fd)
                    closed = os.fstat(fd)
                finally:
                    os.close(fd)
                after = path.lstat()
                if (_stat_fingerprint(opened) != _stat_fingerprint(closed)
                        or _stat_fingerprint(opened) != _stat_fingerprint(after)):
                    changed.append(rel)
            observed = dict(item)
            observed.update({"size": after.st_size, "device": after.st_dev,
                             "inode": after.st_ino, "mode": stat.S_IMODE(after.st_mode),
                             "nlink": after.st_nlink, "mtime_ns": after.st_mtime_ns,
                             "sha256": digest})
            observed_entries.append(observed)
            if item["disposition"] == "text_scanned":
                observed_inputs.append({"path": rel, "sha256": digest, "size": after.st_size})
            metadata_fields = ("size", "device", "inode", "mode", "nlink", "mtime_ns")
            if (any(observed[field] != item[field] for field in metadata_fields)
                    or digest != item["sha256"]
                    or (item["disposition"] == "binary_unscanned" and is_text)):
                changed.append(rel)
        observed_inputs.sort(key=lambda item: item["path"])
        observed_entries_sha = sha_bytes(canonical_bytes(observed_entries))
        observed_inputs_sha = sha_bytes(_canonical_ascii_bytes(observed_inputs))
        changed = sorted(set(changed))
        status = "eligible" if not added and not removed and not changed else "drift"
        return {
            "schema_version": "msae_independent_source_v9_history_recensus_v1",
            "status": status,
            "failure_code": None if status == "eligible" else "history_recensus_drift",
            "expected_entries_sha256": inventory["entries_sha256"],
            "observed_entries_sha256": observed_entries_sha,
            "expected_history_inputs_sha256": inventory["history_inputs_sha256"],
            "observed_history_inputs_sha256": observed_inputs_sha,
            "added_paths": added, "removed_paths": sorted(removed), "changed_paths": changed,
            "quarantine_content_reads": 0,
        }
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, GateFailure) as error:
        code = str(error) if isinstance(error, GateFailure) else "boundary_" + type(error).__name__
        return _failed_history_recensus(inventory, code)


def _current_training_entries(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    expected = {item["path"]: item for item in inventory["training_root_entries"]}
    current: list[dict[str, Any]] = []
    for path, rel in _walk_paths_allow_v9():
        folded = rel.casefold()
        name = Path(folded).name
        if not (folded.startswith("results/") or "checkpoint" in folded
                or name == "train_metrics.jsonl"
                or (folded.startswith("pilot_runs/")
                    and Path(folded).suffix in {".pt", ".pth", ".ckpt", ".safetensors"})):
            continue
        st = path.lstat()
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            current.append({"path": rel, "state": "nonregular", "size": st.st_size,
                            "mode": stat.S_IMODE(st.st_mode), "inode": st.st_ino,
                            "mtime_ns": st.st_mtime_ns})
            continue
        current.append({"path": rel, "size": st.st_size, "mode": stat.S_IMODE(st.st_mode),
                        "inode": st.st_ino, "mtime_ns": st.st_mtime_ns,
                        "sha256": sha_file(path),
                        "disposition": expected.get(rel, {}).get("disposition", "new")})
    return sorted(current, key=lambda item: item["path"])


def _training_recensus(inventory: dict[str, Any]) -> dict[str, Any]:
    expected = inventory["training_root_entries"]
    expected_sha = inventory.get("training_root_entries_sha256", sha_bytes(canonical_bytes(expected)))
    try:
        observed = _current_training_entries(inventory)
        observed_sha = sha_bytes(canonical_bytes(observed))
        status = "eligible" if observed == expected else "drift"
        return {
            "schema_version": "msae_independent_source_v9_training_recensus_v1",
            "status": status,
            "failure_code": None if status == "eligible" else "training_recensus_drift",
            "expected_entries_sha256": expected_sha,
            "observed_entries_sha256": observed_sha,
            "expected_entry_count": len(expected), "observed_entry_count": len(observed),
        }
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, GateFailure) as error:
        code = str(error) if isinstance(error, GateFailure) else "boundary_" + type(error).__name__
        return _failed_training_recensus(inventory, code)


def _post_baseline_inventory(inventory: dict[str, Any], state_name: str,
                             self_path: str | None = None, *,
                             verify_raw_hashes: bool = True) -> dict[str, Any]:
    if state_name not in {"scientific_entry", "B0", "B1", "B2"}:
        raise GateFailure("post_baseline_inventory_state")
    baseline_paths = {item["path"] for item in inventory["entries"]}
    acquisition = strict_json(PROV / "source_acquisition.json")
    raw_expected = acquisition.get("files", {})
    raw_names = sorted((*SOURCE_FILES.values(), "LICENSE.txt"))
    common_files = {
        "reports/provenance/msae_independent_source_v9/baseline_inventory.json",
        "reports/provenance/msae_independent_source_v9/preacquisition_authority_manifest.json",
        "reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md",
        "reports/provenance/msae_independent_source_v9/source_acquisition_entry.json",
        "reports/provenance/msae_independent_source_v9/source_acquisition.json",
        *{f"data/msae_independent_source_v9/raw/{COMMIT}/{name}" for name in raw_names},
    }
    scientific_prefix: list[str] = []
    if state_name == "B1":
        seen_absent = False
        for name in SCIENTIFIC_ARTIFACT_NAMES:
            exists = present_path(PROV / name)
            if exists and seen_absent:
                raise GateFailure("scientific_prefix_drift")
            if exists:
                scientific_prefix.append(name)
            else:
                seen_absent = True
    elif state_name == "B2":
        scientific_prefix = list(SCIENTIFIC_ARTIFACT_NAMES)

    expected_files = set(common_files)
    if state_name == "scientific_entry":
        expected_files.add("reports/provenance/msae_independent_source_v9/scientific_preparation_entry.json")
    elif state_name == "B0":
        expected_files.add("reports/provenance/msae_independent_source_v9/preflight_rejection.json")
    else:
        expected_files.add("reports/provenance/msae_independent_source_v9/scientific_preparation_entry.json")
        expected_files.update(
            f"reports/provenance/msae_independent_source_v9/{name}" for name in scientific_prefix)
        if state_name == "B1":
            expected_files.add("reports/provenance/msae_independent_source_v9/rejection.json")
        expected_payload = present_path(PRIVATE / "blind_payload.jsonl")
        if state_name == "B2" and not expected_payload:
            raise GateFailure("post_baseline_payload_absent")
        if expected_payload:
            expected_files.add("data/msae_independent_source_v9/private/blind_payload.jsonl")

    # History/training recensuses separately bind every baseline path and every
    # unrelated repository addition.  This inventory owns the generated v9
    # protocol universe only; otherwise a history-addition failure could not be
    # represented by its required B0 terminal.
    managed_prefixes = ("reports/provenance/msae_independent_source_v9/",
                        "data/msae_independent_source_v9/")
    managed_singletons = {
        "reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md",
    }
    current_files = {
        rel for _path, rel in _walk_paths_allow_v9(include_v9=True)
        if rel not in baseline_paths
        and (rel.startswith(managed_prefixes) or rel in managed_singletons)
    }
    # The containing artifact is not present while its canonical bytes are
    # being constructed, so represent it non-recursively as the frozen self
    # record while still requiring every other addition exactly.
    current_for_compare = set(current_files)
    if self_path is not None and self_path not in current_for_compare:
        current_for_compare.add(self_path)
    if current_for_compare != expected_files:
        raise GateFailure("post_baseline_inventory_path_drift")

    raw_hashes_verified = state_name in {"B1", "B2"}
    data_root = ROOT / "data/msae_independent_source_v9"
    raw_root = data_root / "raw"
    raw_commit = raw_root / COMMIT
    private_exists = present_path(PRIVATE)
    expected_root_names = ["raw"] + (["private"] if private_exists else [])
    directory_states: dict[Path,os.stat_result]={}
    for directory, expected_mode, expected_names in (
        (data_root, 0o700, sorted(expected_root_names)),
        (raw_root, 0o700, [COMMIT]),
        (raw_commit, 0o555, raw_names),
    ):
        st,names = directory_snapshot_nofollow(directory);directory_states[directory]=st
        if (not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
                or stat.S_IMODE(st.st_mode) != expected_mode
                or names != expected_names):
            raise GateFailure("post_baseline_directory_drift")
    if private_exists:
        private_names = ["blind_payload.jsonl"] if present_path(PRIVATE / "blind_payload.jsonl") else []
        st,names=directory_snapshot_nofollow(PRIVATE);directory_states[PRIVATE]=st
        if (not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
                or stat.S_IMODE(st.st_mode) != 0o700
                or names != private_names):
            raise GateFailure("post_baseline_private_directory_drift")

    entries: list[dict[str, Any]] = []
    directory_paths = (data_root, raw_root, raw_commit) + ((PRIVATE,) if private_exists else ())
    for directory in directory_paths:
        st = directory_states[directory]
        entries.append({"path": directory.relative_to(ROOT).as_posix(), "state": "present",
                        "disposition": "v9_generated_protocol", "type": "directory",
                        "mode": stat.S_IMODE(st.st_mode), "nlink": st.st_nlink, "size": st.st_size})
    for rel in sorted(expected_files):
        if rel == self_path:
            entries.append({"path": rel, "state": "self_canonical_final"})
            continue
        path = ROOT / rel
        is_raw = rel.startswith(f"data/msae_independent_source_v9/raw/{COMMIT}/")
        st = lstat_child_nofollow(raw_commit,path.name) if is_raw else regular_state_nofollow(path)
        if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
            raise GateFailure("post_baseline_nonregular_file")
        item: dict[str, Any] = {
            "path": rel, "state": "present", "disposition": "v9_generated_protocol",
            "type": "regular", "mode": stat.S_IMODE(st.st_mode), "nlink": st.st_nlink,
            "size": st.st_size,
        }
        if is_raw:
            expected = raw_expected.get(path.name)
            if not isinstance(expected, dict) or not isinstance(expected.get("sha256"), str):
                raise GateFailure("post_baseline_raw_authority_drift")
            item["sha256"] = expected["sha256"]
            item["sha256_verification_status"] = (
                "verified_post_entry" if raw_hashes_verified else "deferred_until_post_entry")
            if raw_hashes_verified:
                if verify_raw_hashes and sha_file(path) != item["sha256"]:
                    raise GateFailure("post_baseline_raw_hash_drift")
            else:
                item["content_read"] = False
        elif rel == "data/msae_independent_source_v9/private/blind_payload.jsonl":
            if stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1:
                raise GateFailure("post_baseline_payload_custody")
            item["sha256"] = sha_file(path)
        else:
            if stat.S_IMODE(st.st_mode) != 0o644 or st.st_nlink != 1:
                raise GateFailure("post_baseline_public_custody")
            item["sha256"] = sha_file(path)
        entries.append(item)
    for directory,before in directory_states.items():
        after,_names=directory_snapshot_nofollow(directory)
        if _directory_fingerprint(before)!=_directory_fingerprint(after):
            raise GateFailure("path_identity_changed")
    return {"schema_version": "msae_independent_source_v9_post_baseline_inventory_v1",
            "state": state_name, "entries": sorted(entries, key=lambda item: item["path"])}


def publish_scientific_entry(inventory: dict[str, Any], acquisition: dict[str, Any],
                             snapshot: dict[str, Any], history_recensus: dict[str, Any],
                             training_recensus: dict[str, Any]) -> Path:
    path = PROV / "scientific_preparation_entry.json"
    files = [{"path": name, **{key: acquisition["files"][name][key]
                               for key in ("size", "sha256", "git_blob_sha1", "mode", "nlink")}}
             for name in [*SOURCE_FILES.values(), "LICENSE.txt"]]
    value = {
        "schema_version": "msae_independent_source_v9_scientific_preparation_entry_v1",
        "status": "entered_before_first_v9_raw_open",
        "plan_sha256": sha_file(ROOT / "docs/plan-msae-independent-source-v9.md"),
        "plan_review_sha256": sha_file(ROOT / "reports/adversarial/msae_independent_source_v9_plan_review.md"),
        "builder_sha256": sha_file(Path(__file__)), "carryover_authority_sha256": CARRYOVER_SHA256,
        "baseline_inventory_sha256": sha_file(PROV / "baseline_inventory.json"),
        "authority_manifest_sha256": sha_file(PROV / "preacquisition_authority_manifest.json"),
        "authority_review_sha256": sha_file(ROOT / "reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md"),
        "source_acquisition_entry_sha256": sha_file(PROV / "source_acquisition_entry.json"),
        "source_acquisition_sha256": sha_file(PROV / "source_acquisition.json"),
        "source_commit": COMMIT, "files": files, "history_inputs_sha256": inventory["history_inputs_sha256"],
        "history_registry_sha256": sha_file(PROV / "historical_source_registry.json"),
        "history_recensus": history_recensus,
        "training_recensus": training_recensus,
        "pre_entry_process_snapshot": snapshot,
        "pre_entry_process_snapshot_sha256": sha_bytes(canonical_bytes(snapshot)),
        "training_root_entries_sha256": inventory["training_root_entries_sha256"],
        "post_baseline_inventory": _post_baseline_inventory(
            inventory, "scientific_entry",
            "reports/provenance/msae_independent_source_v9/scientific_preparation_entry.json"),
        "raw_file_open_count_before_entry": 0, "source_content_reported": False,
        "model_operations_initiated": 0, "gpu_queries_initiated": 0, "training_runs_initiated": 0,
        "model_scoring_authorized": False, "k2_or_branch_training_authorized": False,
        "stage_c_authorized": False,
    }
    write_json(path, value)
    return path


def build_ready() -> None:
    global DYNAMIC_PREFLIGHT_STARTED, ENTRY_PUBLICATION_STARTED, RAW_ACCESS_AUTHORIZED
    require_frozen_runtime()
    if validate_static_contract(Path(__file__)):
        raise GateFailure("static_contract")
    # Any pre-existing builder-owned state is either a complete B0/B1/B2
    # terminal (verified idempotently without another source read) or case C.
    # In particular, never resume from an entry-only/prefix-only/temp state.
    initial_public=scientific_artifact_inventory();initial_payload=payload_state()
    if (any(item["state"]!="absent" for item in initial_public["entries"])
            or any(item["state"]!="absent" for item in initial_payload)):
        verify_terminal()
        return
    verify_pre_payload_v9_namespace()
    acquisition = _verify_predecessor_and_raw(read_raw=False)
    DYNAMIC_PREFLIGHT_STARTED = True
    inv=strict_json(PROV/"baseline_inventory.json")
    validate_history_registry_binding(inv)
    raw_additions=_raw_history_additions()
    allowed_additions=raw_additions|{
            "reports/provenance/msae_independent_source_v9/baseline_inventory.json",
            "reports/provenance/msae_independent_source_v9/preacquisition_authority_manifest.json",
            "reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md",
            "reports/provenance/msae_independent_source_v9/source_acquisition_entry.json",
            "reports/provenance/msae_independent_source_v9/source_acquisition.json",
        }
    history_recensus=_history_recensus(inv,allowed_additions)
    training_recensus=_training_recensus(inv)
    now=process_snapshot()
    failure_code=next((value for value in (
        history_recensus.get("failure_code"),training_recensus.get("failure_code"),
        "forbidden_prepare_process" if now["status"]!="eligible" else None) if value is not None),None)
    if failure_code is not None:
        retain_preflight_rejection(failure_code,history_recensus,training_recensus,now)
        verify_terminal()
        return
    ENTRY_PUBLICATION_STARTED = True
    publish_scientific_entry(inv,acquisition,now,history_recensus,training_recensus)
    RAW_ACCESS_AUTHORIZED = True
    _verify_predecessor_and_raw(read_raw=True)
    census=document_group_census();write_json(PROV/"document_group_census.json",census)
    if census["status"]!="eligible":raise GateFailure("unsupported_document_group")
    roles,source_counts=_all_source()
    source_manifest={"schema_version":"msae_independent_source_v9_source_manifest_v1","source_commit":COMMIT,
                     "partitions":source_counts,"source_text_published":False}
    write_json(PROV/"source_manifest.json",source_manifest)
    lic=_license(); write_json(PROV/"license.json",lic)
    if lic["status"]!="eligible":raise GateFailure("license_ineligible")
    raw_hashes={sha_file(RAW/name) for name in [*SOURCE_FILES.values(),"LICENSE.txt"]}
    fam=_source_family(inv,raw_hashes);write_json(PROV/"source_family.json",fam)
    if fam["status"]!="eligible":raise GateFailure("source_family_ineligible")
    pedigree=candidate_pedigree();write_json(PROV/"candidate_pedigree.json",pedigree)
    if pedigree["status"]!="eligible":raise GateFailure("candidate_pedigree_ineligible")
    roles,dedup=deduplicate_roles(roles);write_json(PROV/"dedup.json",dedup)
    rows=_source_rows(roles)
    cross=_role_overlap(rows);write_json(PROV/"cross_role_overlap.json",{"schema_version":"msae_independent_source_v9_cross_role_overlap_v1","blocking_collision_count":len(cross),"blocking_collisions":cross,"status":"eligible" if not cross else "ineligible"})
    if cross:raise GateFailure("cross_role_overlap")
    hits,unit_count,adapter_census=_history_overlap(rows,inv)
    inv["entries_sha256"]=sha_bytes(canonical_bytes(inv["entries"]));write_json(PROV/"history_manifest.json",inv)
    overlap={"schema_version":"msae_independent_source_v9_history_overlap_v1","baseline_inventory_sha256":sha_file(PROV/"baseline_inventory.json"),"history_entries_sha256":inv["entries_sha256"],"history_unit_count":unit_count,"history_adapter_census":adapter_census,"candidate_utterance_count":sum(map(len,rows.values())),"blocking_collision_count":len(hits),"blocking_collisions":hits,"quarantine_content_reads":0,"opaque_binary_history_count":inv["counts"].get("binary_unscanned",0),"status":"eligible" if not hits else "ineligible"}
    write_json(PROV/"history_overlap.json",overlap)
    if hits:raise GateFailure("history_overlap")
    support=_support(rows);support["unsupported_tasks"]=["neutral_prefix_offset","entity_binary","entity_type","source_genre"];write_json(PROV/"support.json",support)
    if support["status"]!="eligible":raise GateFailure("support_ineligible")
    role_manifest={"schema_version":"msae_independent_source_v9_role_manifest_v1","source_commit":COMMIT,"roles":{}}
    for role,upstream in (("discovery","train"),("calibration","dev")):
        vals=rows[role];role_manifest["roles"][role]={"upstream_partition":upstream,"record_count":len(vals),"entries":[{"zero_based_rank":i,"sent_id":x["sent_id"],"source_record_sha256":_source_record_hash(x["sentence"])} for i,x in enumerate(vals)]}
    write_json(PROV/"role_manifest.json",role_manifest)
    split,test_rows=build_split_manifest(rows["C1"]+rows["C2"],dedup,census)
    write_json(PROV/"split_manifest.json",split)
    payload_records=(payload_record(item) for item in test_rows)
    payload=publish_private_jsonl(PRIVATE,"blind_payload.jsonl",payload_records);ps=payload.lstat()
    post=process_snapshot()
    if post["status"]!="eligible":raise GateFailure("forbidden_final_process")
    verify_training_roots(inv)
    write_json(PROV/"post_process_snapshot.json",post)
    artifact_names=["baseline_inventory.json","source_acquisition_entry.json","source_acquisition.json",
                    "scientific_preparation_entry.json","source_family.json","candidate_pedigree.json",
                    "license.json","document_group_census.json","source_manifest.json","dedup.json",
                    "history_manifest.json","history_overlap.json","cross_role_overlap.json","support.json",
                    "role_manifest.json","split_manifest.json","post_process_snapshot.json",
                    "preacquisition_alias_screen.json","historical_source_registry.json",
                    "preacquisition_authority_manifest.json"]
    bindings={name:sha_file(PROV/name) for name in artifact_names}
    plan_sha=sha_file(ROOT/"docs/plan-msae-independent-source-v9.md");review_sha=sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_plan_review.md")
    seal={"schema_version":"msae_independent_source_v9_seal_v1",
          "status":"ready_independently_maintained_non_atis_source_pre_v8_history_screened",
          "source_status":"no_project_source_use_evidence_before_v8_subject_to_enumerated_exclusions",
          "source_maintenance_relation":"independently_maintained_official_non_project_repository",
          "source_family_relation":"non_atis",
          "project_history_boundary":"no_project_source_use_evidence_before_v8_subject_to_enumerated_exclusions",
          "v8_candidate_control_carryover_authority_sha256":CARRYOVER_SHA256,
          "researcher_unawareness_claimed":False,"model_pretraining_independence_claimed":False,
          "global_candidate_content_absence_claimed":False,"general_content_separation_claimed":False,
          "independent_replication_claimed":False,"model_scoring_completed":False,
          "scientific_preparation_entry_sha256":sha_file(PROV/"scientific_preparation_entry.json"),
          "post_baseline_inventory":_post_baseline_inventory(
              inv,"B2","reports/provenance/msae_independent_source_v9/seal.json"),
          "plan_sha256":plan_sha,"plan_review_sha256":review_sha,"program_sha256":sha_file(Path(__file__)),
          "acquisition_runner_sha256":sha_file(ROOT/'scripts/acquire_msae_independent_source_v9.py'),
          "test_sha256":sha_file(ROOT/'tests/test_prepare_msae_independent_source_v9.py'),
          "artifact_sha256":bindings,
          "payload":{"path":"data/msae_independent_source_v9/private/blind_payload.jsonl",
                     "sha256":sha_file(payload),"size":ps.st_size,"record_count":len(test_rows),
                     "mode":stat.S_IMODE(ps.st_mode),"nlink":ps.st_nlink},
          "model_operations_initiated_by_builder":0,"gpu_queries_initiated_by_builder":0,
          "training_runs_initiated_by_builder":0,
          "source_content_reported":False,"model_scoring_authorized":False,
          "k2_or_branch_training_authorized":False,"stage_c_authorized":False,
          "external_observation_scope":"baseline_and_terminal_proc_snapshots_plus_training_root_diff",
          "unsupported_tasks":["neutral_prefix_offset","entity_binary","entity_type","source_genre"],
          "opaque_binary_history_excluded":True,"document_speaker_cluster_inference_authorized":False}
    seal_sha=sha_bytes(canonical_file_bytes(seal))
    write_json(PROV/"no_training_gate.json",{"schema_version":"msae_independent_source_v9_no_training_gate_v1",
        "status":"pending_terminal_seal",
        "terminal_status_if_seal_matches":"ready_independently_maintained_non_atis_source_pre_v8_history_screened",
        "scientific_preparation_entry_sha256":sha_file(PROV/"scientific_preparation_entry.json"),
        "model_scoring_authorized":False,"k2_or_branch_training_authorized":False,
        "stage_c_authorized":False,"seal_sha256":seal_sha})
    write_json(PROV/"seal.json",seal)
    verify_terminal()


def _self_inventory(inventory: dict[str, Any], relative_path: str) -> dict[str, Any]:
    entries=[]
    for item in inventory["entries"]:
        if item["path"]==relative_path:
            entries.append({"path":relative_path,"state":"self_canonical_final"})
        else:
            entries.append(item)
    return {"schema_version":"msae_independent_source_v9_scientific_artifact_inventory_v1",
            "entries":entries}


def _failed_history_recensus(inventory: dict[str, Any], code: str) -> dict[str, Any]:
    return {"schema_version":"msae_independent_source_v9_history_recensus_v1",
            "status":"boundary_failure","failure_code":code,
            "expected_entries_sha256":inventory["entries_sha256"],"observed_entries_sha256":None,
            "expected_history_inputs_sha256":inventory["history_inputs_sha256"],
            "observed_history_inputs_sha256":None,"added_paths":[],"removed_paths":[],
            "changed_paths":[],"quarantine_content_reads":0}


def _failed_training_recensus(inventory: dict[str, Any], code: str) -> dict[str, Any]:
    return {"schema_version":"msae_independent_source_v9_training_recensus_v1",
            "status":"boundary_failure","failure_code":code,
            "expected_entries_sha256":inventory["training_root_entries_sha256"],
            "observed_entries_sha256":None,"expected_entry_count":len(inventory["training_root_entries"]),
            "observed_entry_count":None}


def retain_preflight_rejection(code: str, history: dict[str, Any],
                               training: dict[str, Any], snap: dict[str, Any]) -> None:
    path=PROV/"preflight_rejection.json"
    if present_path(path):return
    inv=strict_json(PROV/"baseline_inventory.json")
    _validate_recensus(history,"history","preflight_rejection_evidence")
    _validate_recensus(training,"training","preflight_rejection_evidence")
    verify_process_snapshot_schema(snap,"preflight_rejection_evidence")
    public=_self_inventory(scientific_artifact_inventory(),
                           "reports/provenance/msae_independent_source_v9/preflight_rejection.json")
    value={"schema_version":"msae_independent_source_v9_preflight_rejection_v1",
           "status":"rejected_before_scientific_entry","failure_code":code,
           "plan_sha256":sha_file(ROOT/"docs/plan-msae-independent-source-v9.md"),
           "plan_review_sha256":sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_plan_review.md"),
           "builder_sha256":sha_file(Path(__file__)),"carryover_authority_sha256":CARRYOVER_SHA256,
           "baseline_inventory_sha256":sha_file(PROV/"baseline_inventory.json"),
           "authority_manifest_sha256":sha_file(PROV/"preacquisition_authority_manifest.json"),
           "authority_review_sha256":sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md"),
           "source_acquisition_entry_sha256":sha_file(PROV/"source_acquisition_entry.json"),
           "source_acquisition_sha256":sha_file(PROV/"source_acquisition.json"),
           "history_inputs_sha256":inv["history_inputs_sha256"],"history_recensus":history,
           "training_recensus":training,"pre_entry_process_snapshot":snap,
           "pre_entry_process_snapshot_sha256":sha_bytes(canonical_bytes(snap)),
           "post_baseline_inventory":_post_baseline_inventory(
               inv,"B0","reports/provenance/msae_independent_source_v9/preflight_rejection.json"),
           "scientific_artifact_inventory":public,"payload_state":payload_state(),
           "raw_file_open_count":0,"source_content_reported":False,
           "model_operations_initiated_by_builder":0,"gpu_queries_initiated_by_builder":0,
           "training_runs_initiated_by_builder":0,"model_scoring_authorized":False,
           "k2_or_branch_training_authorized":False,"stage_c_authorized":False,
           "next_action":"new_reviewed_protocol_only"}
    write_json(path,value)


def retain_rejection(code: str) -> None:
    if present_path(PROV/"seal.json"):
        return
    entry_path=PROV/"scientific_preparation_entry.json"
    if not present_path(entry_path) or RAW_FILE_OPEN_COUNT==0:
        return
    inv=strict_json(PROV/"baseline_inventory.json")
    entry=strict_json(entry_path)
    public=_self_inventory(scientific_artifact_inventory(),
                           "reports/provenance/msae_independent_source_v9/rejection.json")
    value={"schema_version":"msae_independent_source_v9_rejection_v1",
           "status":"rejected_after_scientific_entry","failure_code":code,
           "plan_sha256":sha_file(ROOT/"docs/plan-msae-independent-source-v9.md"),
           "plan_review_sha256":sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_plan_review.md"),
           "builder_sha256":sha_file(Path(__file__)),"carryover_authority_sha256":CARRYOVER_SHA256,
           "baseline_inventory_sha256":sha_file(PROV/"baseline_inventory.json"),
           "authority_manifest_sha256":sha_file(PROV/"preacquisition_authority_manifest.json"),
           "authority_review_sha256":sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md"),
           "source_acquisition_entry_sha256":sha_file(PROV/"source_acquisition_entry.json"),
           "source_acquisition_sha256":sha_file(PROV/"source_acquisition.json"),
           "scientific_preparation_entry_sha256":sha_file(entry_path),
           "history_inputs_sha256":inv["history_inputs_sha256"],
           "history_recensus":entry["history_recensus"],"training_recensus":entry["training_recensus"],
           "pre_entry_process_snapshot":entry["pre_entry_process_snapshot"],
           "pre_entry_process_snapshot_sha256":entry["pre_entry_process_snapshot_sha256"],
           "post_baseline_inventory":_post_baseline_inventory(
               inv,"B1","reports/provenance/msae_independent_source_v9/rejection.json"),
           "scientific_artifact_inventory":public,"payload_state":payload_state(),
           "raw_file_open_count":RAW_FILE_OPEN_COUNT,"source_content_reported":False,
           "model_operations_initiated_by_builder":0,"gpu_queries_initiated_by_builder":0,
           "training_runs_initiated_by_builder":0,"model_scoring_authorized":False,
           "k2_or_branch_training_authorized":False,"stage_c_authorized":False,
           "next_action":"new_reviewed_protocol_only"}
    path=PROV/"rejection.json"
    if not present_path(path):write_json(path,value)

def _is_count(value: Any) -> bool:
    return isinstance(value,int) and not isinstance(value,bool) and value >= 0


def _is_sha(value: Any, length: int = 64) -> bool:
    return isinstance(value,str) and re.fullmatch(rf"[0-9a-f]{{{length}}}",value) is not None


def _validate_inventory_artifact(value: Any, code: str) -> None:
    exact_keys(value,{"schema_version","baseline_head","entry_count","counts","quarantine_content_reads",
        "entries","authority_expected_absent","entries_sha256","status","process_snapshot",
        "training_root_entries","training_root_entries_sha256","history_inputs_sha256",
        "v8_carryover_authority_sha256","v8_carryover_status"},code)
    entries=value["entries"]
    if not isinstance(entries,list) or any(not isinstance(item,dict) for item in entries):raise GateFailure(code)
    common={"path","size","mode","device","inode","nlink","mtime_ns","sha256","disposition",
            "adapter","content_reads","extracted_unit_count"}
    for item in entries:
        keys=set(item);expected=common if item.get("disposition")=="quarantine" else common|{"hardlink_aliases"}
        if item.get("adapter")=="safe_archive_members":expected|={"archive_member_count","archive_members_sha256"}
        if item.get("adapter")=="opaque_archive_outside_bounds":expected|={"archive_member_count"}
        if (keys!=expected or not isinstance(item.get("path"),str)
                or any(not _is_count(item.get(name)) for name in ("size","mode","device","inode","nlink","mtime_ns","content_reads","extracted_unit_count"))
                or item.get("disposition") not in {"text_scanned","archive_scanned","binary_unscanned",
                    "v9_authority","v8_candidate_control_carryover","quarantine"}
                or item.get("adapter") not in {"physical_lines","conllu_sentences","safe_archive_members",
                                               "opaque_archive_outside_bounds","opaque_binary","authority","carryover",
                                               "quarantine_lstat_only"}
                or (item["disposition"]=="quarantine") != (item["sha256"] is None)
                or (item["sha256"] is not None and not _is_sha(item["sha256"]))):raise GateFailure(code)
        if "hardlink_aliases" in item and (not isinstance(item["hardlink_aliases"],list)
                or item["hardlink_aliases"]!=sorted(item["hardlink_aliases"])):raise GateFailure(code)
        if "archive_members_sha256" in item and not _is_sha(item["archive_members_sha256"]):raise GateFailure(code)
    derived=dict(sorted(collections.Counter(item["disposition"] for item in entries).items()))
    training=value["training_root_entries"]
    if (value["schema_version"]!="msae_independent_source_v9_baseline_inventory_v1"
            or value["baseline_head"]!="7e1a6fc7a26a870a4edcf29c96b7cdf3cdbd7faa"
            or value["entry_count"]!=len(entries) or value["counts"]!=derived
            or value["quarantine_content_reads"]!=0 or value["status"]!="eligible"
            or value["v8_carryover_authority_sha256"]!=CARRYOVER_SHA256
            or value["v8_carryover_status"]!="opaque_exact_universe_verified"
            or value["entries_sha256"]!=sha_bytes(canonical_bytes(entries))
            or not _is_sha(value["history_inputs_sha256"])
            or not isinstance(value["authority_expected_absent"],list)
            or value["authority_expected_absent"]!=sorted(set(value["authority_expected_absent"]))
            or not isinstance(training,list)
            or any(not isinstance(item,dict) or set(item)!={"path","size","mode","inode","mtime_ns","sha256","disposition"}
                   for item in training)
            or value["training_root_entries_sha256"]!=sha_bytes(canonical_bytes(training))):raise GateFailure(code)
    verify_process_snapshot_schema(value["process_snapshot"],code)
    if value["process_snapshot"]["status"]!="eligible" or value["process_snapshot"]["forbidden_identity_count"]!=0:
        raise GateFailure(code)


def validate_scientific_artifacts(*, verify_raw_hashes: bool = True) -> None:
    code="scientific_artifact_reconstruction"
    baseline=strict_json(PROV/"baseline_inventory.json");history=strict_json(PROV/"history_manifest.json")
    _validate_inventory_artifact(baseline,code);_validate_inventory_artifact(history,code)
    history_digest=validate_history_registry_binding(baseline)
    if history["history_inputs_sha256"]!=history_digest:
        raise GateFailure(code)
    by_path={item["path"]:item for item in baseline["entries"]}
    history_by_path={item["path"]:item for item in history["entries"]}
    if set(by_path)!=set(history_by_path):raise GateFailure(code)
    for path,item in by_path.items():
        other=history_by_path[path]
        if any(item.get(key)!=other.get(key) for key in set(item)|set(other) if key!="extracted_unit_count"):
            raise GateFailure(code)

    census=exact_keys(strict_json(PROV/"document_group_census.json"),
        {"schema_version","newdoc_marker_count","files","test_group_policy",
         "cross_partition_group_id_count","natural_unit","split_group_unit",
         "document_speaker_cluster_inference_authorized","status"},code)
    if set(census["files"])!=set(SOURCE_FILES.values()):raise GateFailure(code)
    marker_total=0
    for item in census["files"].values():
        exact_keys(item,{"marker_count","sentence_count","group_count","empty_group_count",
                         "orphan_sentence_count","duplicate_group_count","group_id_set_sha256"},code)
        if (any(not _is_count(item[name]) for name in ("marker_count","sentence_count","group_count",
                "empty_group_count","orphan_sentence_count","duplicate_group_count"))
                or not _is_sha(item["group_id_set_sha256"])
                or item["group_count"]!=(item["marker_count"] if item["marker_count"] else item["sentence_count"])):
            raise GateFailure(code)
        marker_total+=item["marker_count"]
    expected_policy=("explicit_newdoc" if census["files"][SOURCE_FILES["test"]]["marker_count"]
                     else "sent_id_as_group")
    if (census["schema_version"]!="msae_independent_source_v9_document_group_census_v1"
            or census["newdoc_marker_count"]!=marker_total
            or census["test_group_policy"]!=expected_policy
            or census["cross_partition_group_id_count"]!=0
            or census["natural_unit"]!="sentence"
            or census["split_group_unit"]!="explicit_document_or_sent_id_fallback"
            or any(item[name]!=0 for item in census["files"].values()
                   for name in ("empty_group_count","orphan_sentence_count","duplicate_group_count"))
            or census["document_speaker_cluster_inference_authorized"] is not False
            or census["status"]!="eligible"):
        raise GateFailure(code)

    source=exact_keys(strict_json(PROV/"source_manifest.json"),
        {"schema_version","source_commit","partitions","source_text_published"},code)
    if set(source["partitions"])!={"train","dev","test"}:raise GateFailure(code)
    for name,item in source["partitions"].items():
        exact_keys(item,{"integer_tokens","multiword_rows","empty_node_rows","sentences","sha256"},code)
        if any(not _is_count(item[key]) for key in ("integer_tokens","multiword_rows","empty_node_rows","sentences")) or not _is_sha(item["sha256"]):raise GateFailure(code)
    if (source["schema_version"]!="msae_independent_source_v9_source_manifest_v1"
            or source["source_commit"]!=COMMIT or source["source_text_published"] is not False):raise GateFailure(code)

    license_value=exact_keys(strict_json(PROV/"license.json"),
        {"schema_version","license_id","license_path","license_sha256","license_url",
         "evidence","obligations","raw_committed","payload_committed","contradiction_count","status"},code)
    if set(license_value["evidence"])!={"LICENSE.txt"}:raise GateFailure(code)
    for evidence in license_value["evidence"].values():
        exact_keys(evidence,{"eligible","positive_occurrence_count","positive_phrase_counts",
                             "positive_url_counts","contradiction_counts","contradiction_count"},code)
        if (evidence["eligible"] is not True
                or not _is_count(evidence["positive_occurrence_count"])
                or evidence["positive_occurrence_count"]<1
                or not _is_count(evidence["contradiction_count"])
                or evidence["contradiction_count"]!=0
                or set(evidence["positive_phrase_counts"])!={" ".join(item) for item in LICENSE_PHRASES}
                or set(evidence["contradiction_counts"])!={" ".join(item) for item in LICENSE_CONTRADICTIONS}
                or any(not _is_count(value) for value in evidence["positive_phrase_counts"].values())
                or any(key not in LICENSE_URLS or not _is_count(value)
                       for key,value in evidence["positive_url_counts"].items())
                or any(not _is_count(value) for value in evidence["contradiction_counts"].values())):
            raise GateFailure(code)
    expected_license_sha=(sha_file(RAW/"LICENSE.txt") if verify_raw_hashes
                          else strict_json(PROV/"source_acquisition.json")["files"]["LICENSE.txt"]["sha256"])
    if (license_value["schema_version"]!="msae_independent_source_v9_license_v1"
            or license_value["license_id"]!="CC-BY-SA-4.0" or license_value["license_path"]!="LICENSE.txt"
            or license_value["license_sha256"]!=expected_license_sha
            or license_value["license_url"]!="https://creativecommons.org/licenses/by-sa/4.0/"
            or license_value["obligations"]!=["attribution","share_alike"]
            or license_value["raw_committed"] is not False or license_value["payload_committed"] is not False
            or license_value["contradiction_count"]!=0 or license_value["status"]!="eligible"):raise GateFailure(code)

    family=exact_keys(strict_json(PROV/"source_family.json"),
        {"schema_version","status","disposition","content_occurrence_count","content_occurrences",
         "pathname_occurrence_count","pathname_occurrences","whole_file_digest_matches",
         "history_inputs_sha256","source_text_published"},code)
    if (family["schema_version"]!="msae_independent_source_v9_source_family_v1" or family["status"]!="eligible"
            or family["disposition"]!="project_source_use_unseen_before_v9"
            or family["content_occurrence_count"]!=0 or family["content_occurrences"]!=[]
            or family["pathname_occurrence_count"]!=0 or family["pathname_occurrences"]!=[]
            or family["whole_file_digest_matches"]!=[]
            or family["history_inputs_sha256"]!=baseline["history_inputs_sha256"]
            or family["source_text_published"] is not False):raise GateFailure(code)

    pedigree=exact_keys(strict_json(PROV/"candidate_pedigree.json"),
        {"schema_version","registry_sha256","candidate_identifier_count","candidate_identifier_sha256",
         "candidate_file_identifier_counts","candidate_file_identifier_sha256",
         "allowed_shared_identifier_sha256","blocking_identifier_sha256","blocking_identifier_count",
         "source_prose_published","status"},code)
    for key in ("candidate_identifier_sha256","allowed_shared_identifier_sha256","blocking_identifier_sha256"):
        if pedigree[key]!=sorted(set(pedigree[key])) or any(not _is_sha(item) for item in pedigree[key]):raise GateFailure(code)
    if (pedigree["schema_version"]!="msae_independent_source_v9_candidate_pedigree_v1"
            or pedigree["registry_sha256"]!=sha_file(PROV/"historical_source_registry.json")
            or pedigree["candidate_identifier_count"]!=len(pedigree["candidate_identifier_sha256"])
            or set(pedigree["candidate_file_identifier_counts"])!=set((*SOURCE_FILES.values(),"LICENSE.txt"))
            or set(pedigree["candidate_file_identifier_sha256"])!=set((*SOURCE_FILES.values(),"LICENSE.txt"))
            or any(not _is_count(value) for value in pedigree["candidate_file_identifier_counts"].values())
            or any(values!=sorted(set(values)) or any(not _is_sha(item) for item in values)
                   or pedigree["candidate_file_identifier_counts"].get(name)!=len(values)
                   for name,values in pedigree["candidate_file_identifier_sha256"].items())
            or any(not set(values)<=set(pedigree["candidate_identifier_sha256"])
                   for values in pedigree["candidate_file_identifier_sha256"].values())
            or not set(pedigree["allowed_shared_identifier_sha256"])<=set(pedigree["candidate_identifier_sha256"])
            or pedigree["blocking_identifier_count"]!=len(pedigree["blocking_identifier_sha256"])
            or pedigree["blocking_identifier_count"]!=0 or pedigree["source_prose_published"] is not False
            or pedigree["status"]!="eligible"):raise GateFailure(code)

    dedup=exact_keys(strict_json(PROV/"dedup.json"),
        {"schema_version","roles","cross_partition_normalized_group_count","source_text_published",
         "test_groups"},code)
    if set(dedup["roles"])!={"discovery","calibration","test"}:raise GateFailure(code)
    expected_upstream={"discovery":"train","calibration":"dev","test":"test"}
    for role,item in dedup["roles"].items():
        exact_keys(item,{"upstream_partition","input_count","retained_count","within_partition_dropped_count",
            "within_partition_dropped_ids_sha256","cross_partition_dropped_count","cross_partition_dropped_ids_sha256"},code)
        if (item["upstream_partition"]!=expected_upstream[role]
                or any(not _is_count(item[key]) for key in ("input_count","retained_count","within_partition_dropped_count","cross_partition_dropped_count"))
                or item["retained_count"]+item["within_partition_dropped_count"]+item["cross_partition_dropped_count"]!=item["input_count"]
                or not _is_sha(item["within_partition_dropped_ids_sha256"])
                or not _is_sha(item["cross_partition_dropped_ids_sha256"])):raise GateFailure(code)
    if (dedup["schema_version"]!="msae_independent_source_v9_dedup_v1"
            or not _is_count(dedup["cross_partition_normalized_group_count"])
            or dedup["source_text_published"] is not False):raise GateFailure(code)
    groups=exact_keys(dedup["test_groups"],{"pre_dedup_group_count","retained_group_count",
        "fully_removed_group_count","fully_removed_group_ids_sha256"},code)
    if (any(not _is_count(groups[name]) for name in ("pre_dedup_group_count","retained_group_count",
            "fully_removed_group_count")) or not _is_sha(groups["fully_removed_group_ids_sha256"])
            or groups["pre_dedup_group_count"]!=groups["retained_group_count"]+groups["fully_removed_group_count"]):
        raise GateFailure(code)

    cross=exact_keys(strict_json(PROV/"cross_role_overlap.json"),
        {"schema_version","blocking_collision_count","blocking_collisions","status"},code)
    if (cross["schema_version"]!="msae_independent_source_v9_cross_role_overlap_v1"
            or cross["blocking_collision_count"]!=len(cross["blocking_collisions"])
            or cross["blocking_collision_count"]!=0 or cross["blocking_collisions"]!=[] or cross["status"]!="eligible"):
        raise GateFailure(code)

    overlap=exact_keys(strict_json(PROV/"history_overlap.json"),
        {"schema_version","baseline_inventory_sha256","history_entries_sha256","history_unit_count",
         "history_adapter_census","candidate_utterance_count","blocking_collision_count","blocking_collisions",
         "quarantine_content_reads","opaque_binary_history_count","status"},code)
    if (overlap["schema_version"]!="msae_independent_source_v9_history_overlap_v1"
            or overlap["baseline_inventory_sha256"]!=sha_file(PROV/"baseline_inventory.json")
            or overlap["history_entries_sha256"]!=history["entries_sha256"]
            or any(not _is_count(overlap[key]) for key in ("history_unit_count","candidate_utterance_count",
                    "blocking_collision_count","quarantine_content_reads","opaque_binary_history_count"))
            or not isinstance(overlap["history_adapter_census"],dict)
            or any(not isinstance(key,str) or not _is_count(value) for key,value in overlap["history_adapter_census"].items())
            or overlap["blocking_collision_count"]!=0 or overlap["blocking_collisions"]!=[]
            or overlap["quarantine_content_reads"]!=0
            or overlap["opaque_binary_history_count"]!=baseline["counts"].get("binary_unscanned",0)
            or overlap["status"]!="eligible"):raise GateFailure(code)

    support=exact_keys(strict_json(PROV/"support.json"),
        {"schema_version","floor_distinct_utterances","roles","all_role_task_intersection","status","unsupported_tasks"},code)
    if set(support["roles"])!={"discovery","calibration","C1","C2"}:raise GateFailure(code)
    eligible_sets=[]
    for role,item in support["roles"].items():
        exact_keys(item,{"utterance_count","tasks"},code)
        if not _is_count(item["utterance_count"]) or set(item["tasks"])!=set(TASKS):raise GateFailure(code)
        eligible=set()
        for task,record in item["tasks"].items():
            exact_keys(record,{"eligible","retained_class_count","distinct_utterances_by_class"},code)
            classes=record["distinct_utterances_by_class"]
            if (not isinstance(classes,dict) or any(not isinstance(key,str) or not _is_count(value)
                    or value<20 or value>item["utterance_count"] for key,value in classes.items())
                    or record["retained_class_count"]!=len(classes) or record["eligible"] is not (len(classes)>=2)):
                raise GateFailure(code)
            if record["eligible"]:eligible.add(task)
        eligible_sets.append(eligible)
    intersection=set.intersection(*eligible_sets)
    if (support["schema_version"]!="msae_independent_source_v9_support_v1" or support["floor_distinct_utterances"]!=20
            or support["all_role_task_intersection"]!=sorted(intersection)
            or support["status"]!="eligible" or not REQUIRED<=intersection or len(OPTIONAL&intersection)<2
            or support["unsupported_tasks"]!=["neutral_prefix_offset","entity_binary","entity_type","source_genre"]):raise GateFailure(code)

    post=strict_json(PROV/"post_process_snapshot.json");verify_process_snapshot_schema(post,code)
    if post["status"]!="eligible" or post["forbidden_identity_count"]!=0:raise GateFailure(code)


def reconstruct_scientific_artifacts() -> dict[str, Any]:
    """Re-run the deterministic, model-free source pipeline and require byte-exact public evidence."""
    code="scientific_artifact_exact_reconstruction"
    baseline=strict_json(PROV/"baseline_inventory.json")
    census=document_group_census()
    if strict_json(PROV/"document_group_census.json")!=census:raise GateFailure(code)
    roles,source_counts=_all_source()
    source={"schema_version":"msae_independent_source_v9_source_manifest_v1","source_commit":COMMIT,
            "partitions":source_counts,"source_text_published":False}
    if strict_json(PROV/"source_manifest.json")!=source:raise GateFailure(code)
    if strict_json(PROV/"license.json")!=_license():raise GateFailure(code)
    raw_hashes={sha_file(RAW/name) for name in [*SOURCE_FILES.values(),"LICENSE.txt"]}
    if strict_json(PROV/"source_family.json")!=_source_family(baseline,raw_hashes):raise GateFailure(code)
    if strict_json(PROV/"candidate_pedigree.json")!=candidate_pedigree():raise GateFailure(code)
    roles,dedup=deduplicate_roles(roles)
    if strict_json(PROV/"dedup.json")!=dedup:raise GateFailure(code)
    rows=_source_rows(roles);cross=_role_overlap(rows)
    cross_value={"schema_version":"msae_independent_source_v9_cross_role_overlap_v1",
                 "blocking_collision_count":len(cross),"blocking_collisions":cross,
                 "status":"eligible" if not cross else "ineligible"}
    if strict_json(PROV/"cross_role_overlap.json")!=cross_value:raise GateFailure(code)
    hits,unit_count,adapter_census=_history_overlap(rows,baseline)
    baseline["entries_sha256"]=sha_bytes(canonical_bytes(baseline["entries"]))
    if strict_json(PROV/"history_manifest.json")!=baseline:raise GateFailure(code)
    overlap={"schema_version":"msae_independent_source_v9_history_overlap_v1",
        "baseline_inventory_sha256":sha_file(PROV/"baseline_inventory.json"),
        "history_entries_sha256":baseline["entries_sha256"],"history_unit_count":unit_count,
        "history_adapter_census":adapter_census,"candidate_utterance_count":sum(map(len,rows.values())),
        "blocking_collision_count":len(hits),"blocking_collisions":hits,"quarantine_content_reads":0,
        "opaque_binary_history_count":baseline["counts"].get("binary_unscanned",0),
        "status":"eligible" if not hits else "ineligible"}
    if strict_json(PROV/"history_overlap.json")!=overlap:raise GateFailure(code)
    support=_support(rows);support["unsupported_tasks"]=["neutral_prefix_offset","entity_binary","entity_type","source_genre"]
    if strict_json(PROV/"support.json")!=support:raise GateFailure(code)
    role_manifest={"schema_version":"msae_independent_source_v9_role_manifest_v1","source_commit":COMMIT,"roles":{}}
    for role,upstream in (("discovery","train"),("calibration","dev")):
        values=rows[role]
        role_manifest["roles"][role]={"upstream_partition":upstream,"record_count":len(values),
            "entries":[{"zero_based_rank":i,"sent_id":item["sent_id"],
                        "source_record_sha256":_source_record_hash(item["sentence"])} for i,item in enumerate(values)]}
    if strict_json(PROV/"role_manifest.json")!=role_manifest:raise GateFailure(code)
    split,test_rows=build_split_manifest(rows["C1"]+rows["C2"],dedup,census)
    if strict_json(PROV/"split_manifest.json")!=split:raise GateFailure(code)
    payload_bytes=b"".join(canonical_file_bytes(payload_record(item)) for item in test_rows)
    return {"sha256":sha_bytes(payload_bytes),"size":len(payload_bytes),"record_count":len(test_rows)}


def _validate_recensus(value: Any, kind: str, code: str) -> None:
    if kind == "history":
        exact_keys(value,{"schema_version","status","failure_code","expected_entries_sha256",
            "observed_entries_sha256","expected_history_inputs_sha256","observed_history_inputs_sha256",
            "added_paths","removed_paths","changed_paths","quarantine_content_reads"},code)
        if (value.get("schema_version")!="msae_independent_source_v9_history_recensus_v1"
                or value.get("status") not in {"eligible","drift","boundary_failure"}
                or not _is_sha(value.get("expected_entries_sha256"))
                or not _is_sha(value.get("expected_history_inputs_sha256"))
                or value.get("quarantine_content_reads")!=0
                or any(not isinstance(value.get(name),list)
                       or value[name]!=sorted(set(value[name]))
                       or any(not isinstance(item,str) or not item for item in value[name])
                       for name in ("added_paths","removed_paths","changed_paths"))):
            raise GateFailure(code)
        observed=(value.get("observed_entries_sha256"),value.get("observed_history_inputs_sha256"))
    else:
        exact_keys(value,{"schema_version","status","failure_code","expected_entries_sha256",
            "observed_entries_sha256","expected_entry_count","observed_entry_count"},code)
        if (value.get("schema_version")!="msae_independent_source_v9_training_recensus_v1"
                or value.get("status") not in {"eligible","drift","boundary_failure"}
                or not _is_sha(value.get("expected_entries_sha256"))
                or not _is_count(value.get("expected_entry_count"))):
            raise GateFailure(code)
        observed=(value.get("observed_entries_sha256"),value.get("observed_entry_count"))
    if ((value["status"]=="eligible") != (value.get("failure_code") is None)
            or (value["status"]=="boundary_failure") != all(item is None for item in observed)
            or value["status"]!="boundary_failure" and any(item is None for item in observed)):
        raise GateFailure(code)
    if value["status"]!="boundary_failure" and not _is_sha(observed[0]):
        raise GateFailure(code)
    if kind=="training" and value["status"]!="boundary_failure" and not _is_count(observed[1]):
        raise GateFailure(code)


def _terminal_common(value: dict[str,Any], baseline: dict[str,Any], code: str) -> None:
    if (not isinstance(value.get("failure_code"),str) or not value["failure_code"]
            or value.get("plan_sha256")!=sha_file(ROOT/"docs/plan-msae-independent-source-v9.md")
            or value.get("plan_review_sha256")!=sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_plan_review.md")
            or value.get("builder_sha256")!=sha_file(Path(__file__))
            or value.get("carryover_authority_sha256")!=CARRYOVER_SHA256
            or value.get("baseline_inventory_sha256")!=sha_file(PROV/"baseline_inventory.json")
            or value.get("authority_manifest_sha256")!=sha_file(PROV/"preacquisition_authority_manifest.json")
            or value.get("authority_review_sha256")!=sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md")
            or value.get("source_acquisition_entry_sha256")!=sha_file(PROV/"source_acquisition_entry.json")
            or value.get("source_acquisition_sha256")!=sha_file(PROV/"source_acquisition.json")
            or value.get("history_inputs_sha256")!=baseline.get("history_inputs_sha256")
            or value.get("pre_entry_process_snapshot_sha256")!=sha_bytes(canonical_bytes(value.get("pre_entry_process_snapshot")))
            or not _is_count(value.get("raw_file_open_count"))
            or value.get("source_content_reported") is not False
            or value.get("model_operations_initiated_by_builder")!=0
            or value.get("gpu_queries_initiated_by_builder")!=0
            or value.get("training_runs_initiated_by_builder")!=0
            or value.get("model_scoring_authorized") is not False
            or value.get("k2_or_branch_training_authorized") is not False
            or value.get("stage_c_authorized") is not False
            or value.get("next_action")!="new_reviewed_protocol_only"):
        raise GateFailure(code)
    _validate_recensus(value.get("history_recensus"),"history",code)
    _validate_recensus(value.get("training_recensus"),"training",code)
    verify_process_snapshot_schema(value.get("pre_entry_process_snapshot"),code)


def _verify_terminal_entry(baseline: dict[str,Any]) -> dict[str,Any]:
    code="scientific_entry_verification"
    path=PROV/"scientific_preparation_entry.json"
    entry=strict_terminal_json(path)
    exact_keys(entry,{"schema_version","status","plan_sha256","plan_review_sha256","builder_sha256",
        "carryover_authority_sha256","baseline_inventory_sha256","authority_manifest_sha256",
        "authority_review_sha256","source_acquisition_entry_sha256","source_acquisition_sha256",
        "source_commit","files","history_inputs_sha256","history_registry_sha256","history_recensus",
        "training_recensus","pre_entry_process_snapshot","pre_entry_process_snapshot_sha256",
        "training_root_entries_sha256","post_baseline_inventory","raw_file_open_count_before_entry",
        "source_content_reported","model_operations_initiated","gpu_queries_initiated",
        "training_runs_initiated","model_scoring_authorized","k2_or_branch_training_authorized",
        "stage_c_authorized"},code)
    acquisition=strict_json(PROV/"source_acquisition.json")
    names=[*SOURCE_FILES.values(),"LICENSE.txt"]
    expected_files=[{"path":name,**{key:acquisition["files"][name][key]
                     for key in ("size","sha256","git_blob_sha1","mode","nlink")}} for name in names]
    if (entry.get("schema_version")!="msae_independent_source_v9_scientific_preparation_entry_v1"
            or entry.get("status")!="entered_before_first_v9_raw_open"
            or entry.get("plan_sha256")!=sha_file(ROOT/"docs/plan-msae-independent-source-v9.md")
            or entry.get("plan_review_sha256")!=sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_plan_review.md")
            or entry.get("builder_sha256")!=sha_file(Path(__file__))
            or entry.get("carryover_authority_sha256")!=CARRYOVER_SHA256
            or entry.get("baseline_inventory_sha256")!=sha_file(PROV/"baseline_inventory.json")
            or entry.get("authority_manifest_sha256")!=sha_file(PROV/"preacquisition_authority_manifest.json")
            or entry.get("authority_review_sha256")!=sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md")
            or entry.get("source_acquisition_entry_sha256")!=sha_file(PROV/"source_acquisition_entry.json")
            or entry.get("source_acquisition_sha256")!=sha_file(PROV/"source_acquisition.json")
            or entry.get("source_commit")!=COMMIT or entry.get("files")!=expected_files
            or entry.get("history_inputs_sha256")!=baseline.get("history_inputs_sha256")
            or entry.get("history_registry_sha256")!=sha_file(PROV/"historical_source_registry.json")
            or entry.get("training_root_entries_sha256")!=baseline.get("training_root_entries_sha256")
            or entry.get("pre_entry_process_snapshot_sha256")!=sha_bytes(canonical_bytes(entry.get("pre_entry_process_snapshot")))
            or entry.get("raw_file_open_count_before_entry")!=0
            or entry.get("source_content_reported") is not False
            or any(entry.get(name)!=0 for name in ("model_operations_initiated","gpu_queries_initiated","training_runs_initiated"))
            or any(entry.get(name) is not False for name in ("model_scoring_authorized",
                "k2_or_branch_training_authorized","stage_c_authorized"))):
        raise GateFailure(code)
    _validate_recensus(entry.get("history_recensus"),"history",code)
    _validate_recensus(entry.get("training_recensus"),"training",code)
    if entry["history_recensus"]["status"]!="eligible" or entry["training_recensus"]["status"]!="eligible":
        raise GateFailure(code)
    verify_process_snapshot_schema(entry.get("pre_entry_process_snapshot"),code)
    if entry["pre_entry_process_snapshot"]["status"]!="eligible":raise GateFailure(code)
    expected_inventory=_post_baseline_inventory(
        baseline,"scientific_entry",
        "reports/provenance/msae_independent_source_v9/scientific_preparation_entry.json",
        verify_raw_hashes=False)
    if entry.get("post_baseline_inventory")!=expected_inventory:raise GateFailure(code)
    return entry


def _regular_additions(post_inventory: dict[str,Any]) -> set[str]:
    return {item["path"] for item in post_inventory.get("entries",[])
            if item.get("type")=="regular" or item.get("state")=="self_canonical_final"}


def _verify_terminal_recensuses(baseline: dict[str, Any], additions: set[str],
                                expected_history: dict[str, Any],
                                expected_training: dict[str, Any], code: str) -> None:
    current_history = _history_recensus(baseline, additions)
    current_training = _training_recensus(baseline)
    if current_history != expected_history or current_training != expected_training:
        raise GateFailure(code)


def verify_terminal() -> None:
    finals=scientific_artifact_inventory();states={item["path"]:item for item in finals["entries"]}
    if any(item["state"]!="absent" for item in finals["entries"][1::2]):
        raise GateFailure("terminal_state_cardinality")
    preflight_path=PROV/"preflight_rejection.json";entry_path=PROV/"scientific_preparation_entry.json"
    rejection_path=PROV/"rejection.json";seal_path=PROV/"seal.json"
    present_finals={path for path,item in states.items() if not path.endswith(".building") and item["state"]=="present"}
    sci_paths=[f"reports/provenance/msae_independent_source_v9/{name}" for name in SCIENTIFIC_ARTIFACT_NAMES]
    entry_rel="reports/provenance/msae_independent_source_v9/scientific_preparation_entry.json"
    preflight_rel="reports/provenance/msae_independent_source_v9/preflight_rejection.json"
    rejection_rel="reports/provenance/msae_independent_source_v9/rejection.json"
    payload_now=payload_state()
    if payload_now[1]["state"]!="absent":raise GateFailure("terminal_state_cardinality")

    is_b0=present_finals=={preflight_rel} and payload_now[0]["state"]=="absent"
    prefix=[];gap=False;prefix_valid=True
    for path in sci_paths:
        if path in present_finals:
            if gap:prefix_valid=False
            prefix.append(path)
        else:gap=True
    is_b1=(entry_rel in present_finals and rejection_rel in present_finals
           and preflight_rel not in present_finals and prefix_valid
           and present_finals=={entry_rel,rejection_rel,*prefix}
           and "reports/provenance/msae_independent_source_v9/seal.json" not in prefix)
    is_b2=(present_finals=={entry_rel,*sci_paths}
           and payload_now[0].get("state")=="present")
    if sum((is_b0,is_b1,is_b2))!=1:raise GateFailure("terminal_state_cardinality")

    baseline=strict_json(PROV/"baseline_inventory.json")
    _validate_inventory_artifact(baseline,"terminal_baseline_verification")
    validate_history_registry_binding(baseline)
    _verify_predecessor_and_raw(read_raw=False)

    if is_b0:
        value=strict_terminal_json(preflight_path);code="preflight_rejection_verification"
        exact_keys(value,{"schema_version","status","failure_code","plan_sha256","plan_review_sha256",
            "builder_sha256","carryover_authority_sha256","baseline_inventory_sha256",
            "authority_manifest_sha256","authority_review_sha256","source_acquisition_entry_sha256",
            "source_acquisition_sha256","history_inputs_sha256","history_recensus","training_recensus",
            "pre_entry_process_snapshot","pre_entry_process_snapshot_sha256","post_baseline_inventory",
            "scientific_artifact_inventory","payload_state","raw_file_open_count","source_content_reported",
            "model_operations_initiated_by_builder","gpu_queries_initiated_by_builder",
            "training_runs_initiated_by_builder","model_scoring_authorized",
            "k2_or_branch_training_authorized","stage_c_authorized","next_action"},code)
        _terminal_common(value,baseline,code)
        if (value.get("schema_version")!="msae_independent_source_v9_preflight_rejection_v1"
                or value.get("status")!="rejected_before_scientific_entry"
                or value.get("raw_file_open_count")!=0):raise GateFailure(code)
        expected_post=_post_baseline_inventory(baseline,"B0",preflight_rel,verify_raw_hashes=False)
        expected_public=_self_inventory(finals,preflight_rel)
        if (value.get("post_baseline_inventory")!=expected_post
                or value.get("scientific_artifact_inventory")!=expected_public
                or value.get("payload_state")!=payload_now):raise GateFailure(code)
        _verify_terminal_recensuses(
            baseline,_regular_additions(expected_post),value["history_recensus"],
            value["training_recensus"],code)
        return

    entry=_verify_terminal_entry(baseline)
    if is_b1:
        value=strict_terminal_json(rejection_path);code="rejection_verification"
        exact_keys(value,{"schema_version","status","failure_code","plan_sha256","plan_review_sha256",
            "builder_sha256","carryover_authority_sha256","baseline_inventory_sha256",
            "authority_manifest_sha256","authority_review_sha256","source_acquisition_entry_sha256",
            "source_acquisition_sha256","scientific_preparation_entry_sha256","history_inputs_sha256",
            "history_recensus","training_recensus","pre_entry_process_snapshot",
            "pre_entry_process_snapshot_sha256","post_baseline_inventory","scientific_artifact_inventory",
            "payload_state","raw_file_open_count","source_content_reported",
            "model_operations_initiated_by_builder","gpu_queries_initiated_by_builder",
            "training_runs_initiated_by_builder","model_scoring_authorized",
            "k2_or_branch_training_authorized","stage_c_authorized","next_action"},code)
        _terminal_common(value,baseline,code)
        if (value.get("schema_version")!="msae_independent_source_v9_rejection_v1"
                or value.get("status")!="rejected_after_scientific_entry"
                or value.get("raw_file_open_count",0)<1
                or value.get("scientific_preparation_entry_sha256")!=sha_file(entry_path)
                or value.get("history_recensus")!=entry["history_recensus"]
                or value.get("training_recensus")!=entry["training_recensus"]
                or value.get("pre_entry_process_snapshot")!=entry["pre_entry_process_snapshot"]):
            raise GateFailure(code)
        expected_post=_post_baseline_inventory(baseline,"B1",rejection_rel,verify_raw_hashes=False)
        expected_public=_self_inventory(finals,rejection_rel)
        if (value.get("post_baseline_inventory")!=expected_post
                or value.get("scientific_artifact_inventory")!=expected_public
                or value.get("payload_state")!=payload_now):raise GateFailure(code)
        _verify_terminal_recensuses(
            baseline,_regular_additions(expected_post),entry["history_recensus"],
            entry["training_recensus"],code)
        return

    seal=strict_terminal_json(seal_path)
    exact_keys(seal,{"schema_version","status","source_status","source_maintenance_relation",
        "source_family_relation","project_history_boundary","v8_candidate_control_carryover_authority_sha256",
        "researcher_unawareness_claimed","model_pretraining_independence_claimed",
        "global_candidate_content_absence_claimed","general_content_separation_claimed",
        "independent_replication_claimed","model_scoring_completed","scientific_preparation_entry_sha256",
        "post_baseline_inventory","plan_sha256","plan_review_sha256","program_sha256",
        "acquisition_runner_sha256","test_sha256","artifact_sha256","payload",
        "model_operations_initiated_by_builder","gpu_queries_initiated_by_builder",
        "training_runs_initiated_by_builder","source_content_reported","model_scoring_authorized",
        "k2_or_branch_training_authorized","stage_c_authorized","external_observation_scope",
        "unsupported_tasks","opaque_binary_history_excluded",
        "document_speaker_cluster_inference_authorized"},"seal_verification")
    if (seal.get("schema_version")!="msae_independent_source_v9_seal_v1"
            or seal.get("status")!="ready_independently_maintained_non_atis_source_pre_v8_history_screened"
            or seal.get("source_status")!="no_project_source_use_evidence_before_v8_subject_to_enumerated_exclusions"
            or seal.get("source_maintenance_relation")!="independently_maintained_official_non_project_repository"
            or seal.get("source_family_relation")!="non_atis"
            or seal.get("project_history_boundary")!="no_project_source_use_evidence_before_v8_subject_to_enumerated_exclusions"
            or seal.get("v8_candidate_control_carryover_authority_sha256")!=CARRYOVER_SHA256
            or any(seal.get(name) is not False for name in ("researcher_unawareness_claimed",
                "model_pretraining_independence_claimed","global_candidate_content_absence_claimed",
                "general_content_separation_claimed","independent_replication_claimed","model_scoring_completed"))
            or seal.get("scientific_preparation_entry_sha256")!=sha_file(entry_path)
            or seal.get("plan_sha256")!=sha_file(ROOT/"docs/plan-msae-independent-source-v9.md")
            or seal.get("plan_review_sha256")!=sha_file(ROOT/"reports/adversarial/msae_independent_source_v9_plan_review.md")
            or seal.get("program_sha256")!=sha_file(Path(__file__))
            or seal.get("acquisition_runner_sha256")!=sha_file(ROOT/"scripts/acquire_msae_independent_source_v9.py")
            or seal.get("test_sha256")!=sha_file(ROOT/"tests/test_prepare_msae_independent_source_v9.py")
            or seal.get("model_operations_initiated_by_builder")!=0
            or seal.get("gpu_queries_initiated_by_builder")!=0
            or seal.get("training_runs_initiated_by_builder")!=0
            or seal.get("source_content_reported") is not False
            or seal.get("model_scoring_authorized") is not False
            or seal.get("k2_or_branch_training_authorized") is not False
            or seal.get("stage_c_authorized") is not False
            or seal.get("external_observation_scope")!="baseline_and_terminal_proc_snapshots_plus_training_root_diff"
            or seal.get("unsupported_tasks")!=["neutral_prefix_offset","entity_binary","entity_type","source_genre"]
            or seal.get("opaque_binary_history_excluded") is not True
            or seal.get("document_speaker_cluster_inference_authorized") is not False):
        raise GateFailure("seal_verification")
    expected_post=_post_baseline_inventory(
        baseline,"B2","reports/provenance/msae_independent_source_v9/seal.json",verify_raw_hashes=False)
    if seal.get("post_baseline_inventory")!=expected_post:raise GateFailure("seal_verification")
    _verify_terminal_recensuses(
        baseline,_regular_additions(expected_post),entry["history_recensus"],
        entry["training_recensus"],"seal_verification")
    expected_artifacts={
        "baseline_inventory.json","source_acquisition_entry.json","source_acquisition.json","scientific_preparation_entry.json",
        "source_family.json","candidate_pedigree.json","license.json",
        "document_group_census.json","source_manifest.json","dedup.json","history_manifest.json","history_overlap.json",
        "cross_role_overlap.json","support.json","role_manifest.json","split_manifest.json","post_process_snapshot.json",
        "preacquisition_alias_screen.json","historical_source_registry.json","preacquisition_authority_manifest.json"}
    bindings=seal.get("artifact_sha256",{})
    if set(bindings)!=expected_artifacts or any(sha_file(PROV/name)!=digest for name,digest in bindings.items()):
        raise GateFailure("seal_artifact_binding")
    expected_schemas={
        "baseline_inventory.json":"msae_independent_source_v9_baseline_inventory_v1",
        "source_acquisition_entry.json":"msae_independent_source_v9_source_acquisition_entry_v1",
        "source_acquisition.json":"msae_independent_source_v9_source_acquisition_v1",
        "scientific_preparation_entry.json":"msae_independent_source_v9_scientific_preparation_entry_v1",
        "source_family.json":"msae_independent_source_v9_source_family_v1",
        "candidate_pedigree.json":"msae_independent_source_v9_candidate_pedigree_v1",
        "license.json":"msae_independent_source_v9_license_v1",
        "document_group_census.json":"msae_independent_source_v9_document_group_census_v1",
        "source_manifest.json":"msae_independent_source_v9_source_manifest_v1",
        "dedup.json":"msae_independent_source_v9_dedup_v1",
        "history_manifest.json":"msae_independent_source_v9_baseline_inventory_v1",
        "history_overlap.json":"msae_independent_source_v9_history_overlap_v1",
        "cross_role_overlap.json":"msae_independent_source_v9_cross_role_overlap_v1",
        "support.json":"msae_independent_source_v9_support_v1",
        "role_manifest.json":"msae_independent_source_v9_role_manifest_v1",
        "split_manifest.json":"msae_independent_source_v9_split_manifest_v1",
        "post_process_snapshot.json":"msae_independent_source_v9_process_snapshot_v1",
        "preacquisition_alias_screen.json":"msae_independent_source_v9_preacquisition_alias_screen_v2",
        "historical_source_registry.json":"msae_independent_source_v9_historical_source_registry_v1",
        "preacquisition_authority_manifest.json":"msae_independent_source_v9_preacquisition_authority_v1",
    }
    for name,schema in expected_schemas.items():
        if strict_json(PROV/name).get("schema_version")!=schema:raise GateFailure("artifact_schema_verification")
    validate_scientific_artifacts(verify_raw_hashes=False)
    reconstructed_payload={key:seal["payload"][key] for key in ("sha256","size","record_count")}
    split=strict_json(PROV/"split_manifest.json");entries=split.get("entries",[])
    exact_keys(split,{"schema_version","source_commit","upstream_partition","test_group_policy",
                      "split_algorithm","pre_dedup_group_count","retained_group_count",
                      "fully_removed_group_count","group_count","C1_group_count","C2_group_count",
                      "record_count","C1_count","C2_count","entries"},"split_manifest_verification")
    if (any(not isinstance(item,dict) or set(item)!={"sent_id","panel","group_rank","within_group_rank",
            "group_key_sha256","group_id_sha256","source_record_sha256"} for item in entries)
            or split.get("schema_version")!="msae_independent_source_v9_split_manifest_v1"
            or split.get("source_commit")!=COMMIT
            or split.get("test_group_policy") not in {"explicit_newdoc","sent_id_as_group"}
            or split.get("split_algorithm")!="sha256-canonical-json-group-v1-even-C1-odd-C2"
            or split.get("record_count")!=len(entries)
            or split.get("C1_count")!=sum(item.get("panel")=="C1" for item in entries)
            or split.get("C2_count")!=sum(item.get("panel")=="C2" for item in entries)
            or split.get("upstream_partition")!="test"
            or any(not isinstance(item.get("sent_id"),str) or not item.get("sent_id")
                   or not _is_count(item.get("group_rank")) or not _is_count(item.get("within_group_rank"))
                   or item.get("panel")!=("C1" if item.get("group_rank",-1)%2==0 else "C2")
                   for item in entries)
            or any(not re.fullmatch(r"[0-9a-f]{64}",str(item.get("group_key_sha256","")))
                   or not re.fullmatch(r"[0-9a-f]{64}",str(item.get("group_id_sha256",""))) for item in entries)
            or any(not re.fullmatch(r"[0-9a-f]{64}",str(item.get("source_record_sha256",""))) for item in entries)):
        raise GateFailure("split_manifest_verification")
    grouped: dict[int,list[dict[str,Any]]]=collections.defaultdict(list)
    for item in entries:grouped[item["group_rank"]].append(item)
    if (entries!=sorted(entries,key=lambda item:(item["group_rank"],item["within_group_rank"]))
            or split.get("pre_dedup_group_count")!=split.get("retained_group_count",-1)+split.get("fully_removed_group_count",-1)
            or split.get("retained_group_count")!=split.get("group_count")
            or split.get("group_count")!=len(grouped)
            or sorted(grouped)!=list(range(len(grouped)))
            or split.get("C1_group_count")!=sum(rank%2==0 for rank in grouped)
            or split.get("C2_group_count")!=sum(rank%2==1 for rank in grouped)
            or any([item["within_group_rank"] for item in group]!=list(range(len(group)))
                   or len({item["panel"] for item in group})!=1
                   or len({item["group_key_sha256"] for item in group})!=1
                   or len({item["group_id_sha256"] for item in group})!=1
                   for group in grouped.values())):
        raise GateFailure("split_manifest_verification")
    roles=strict_json(PROV/"role_manifest.json")
    exact_keys(roles,{"schema_version","source_commit","roles"},"role_manifest_verification")
    role_values=roles.get("roles",{})
    if (roles.get("schema_version")!="msae_independent_source_v9_role_manifest_v1"
            or set(role_values)!={"discovery","calibration"}
            or roles.get("source_commit")!=COMMIT
            or any(set(item)!={"upstream_partition","record_count","entries"}
                   or item.get("upstream_partition")!={"discovery":"train","calibration":"dev"}[role]
                   or item.get("record_count")!=len(item.get("entries",[]))
                   or [entry.get("zero_based_rank") for entry in item.get("entries",[])]!=list(range(item.get("record_count",-1)))
                   or any(set(entry)!={"zero_based_rank","sent_id","source_record_sha256"}
                          or not isinstance(entry.get("sent_id"),str)
                          or not re.fullmatch(r"[0-9a-f]{64}",str(entry.get("source_record_sha256","")))
                          for entry in item.get("entries",[])) for role,item in role_values.items())):
        raise GateFailure("role_manifest_verification")
    source=strict_json(PROV/"source_manifest.json");dedup=strict_json(PROV/"dedup.json")
    source_parts=source.get("partitions",{});dedup_roles=dedup.get("roles",{})
    dedup_groups=dedup.get("test_groups",{})
    support=strict_json(PROV/"support.json");support_roles=support.get("roles",{})
    if (source.get("source_commit")!=COMMIT or set(source_parts)!={"train","dev","test"}
            or set(dedup_roles)!={"discovery","calibration","test"}
            or set(support_roles)!={"discovery","calibration","C1","C2"}
            or source_parts["train"].get("sentences")!=dedup_roles["discovery"].get("input_count")
            or source_parts["dev"].get("sentences")!=dedup_roles["calibration"].get("input_count")
            or source_parts["test"].get("sentences")!=dedup_roles["test"].get("input_count")
            or dedup_roles["discovery"].get("retained_count")!=role_values["discovery"].get("record_count")
            or dedup_roles["calibration"].get("retained_count")!=role_values["calibration"].get("record_count")
            or dedup_roles["test"].get("retained_count")!=len(entries)
            or dedup_groups.get("pre_dedup_group_count")!=split.get("pre_dedup_group_count")
            or dedup_groups.get("retained_group_count")!=split.get("retained_group_count")
            or dedup_groups.get("fully_removed_group_count")!=split.get("fully_removed_group_count")
            or support_roles["discovery"].get("utterance_count")!=role_values["discovery"].get("record_count")
            or support_roles["calibration"].get("utterance_count")!=role_values["calibration"].get("record_count")
            or support_roles["C1"].get("utterance_count")!=split.get("C1_count")
            or support_roles["C2"].get("utterance_count")!=split.get("C2_count")
            or strict_json(PROV/"history_overlap.json").get("candidate_utterance_count")!=
                sum(item.get("utterance_count",0) for item in support_roles.values())):
        raise GateFailure("cross_artifact_count_verification")
    for name in ("source_family.json","candidate_pedigree.json","license.json","document_group_census.json","history_overlap.json","cross_role_overlap.json","support.json","post_process_snapshot.json"):
        if strict_json(PROV/name).get("status")!="eligible":raise GateFailure("ineligible_sealed_artifact")
    payload_item=exact_keys(seal["payload"],{"path","sha256","size","record_count","mode","nlink"},"payload_verification")
    payload=ROOT/payload_item["path"];st=payload.lstat()
    if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode)!=0o600 or st.st_nlink!=1
            or st.st_size!=payload_item["size"] or payload_item["record_count"]!=len(entries)
            or {key:payload_item[key] for key in ("sha256","size","record_count")}!=reconstructed_payload
            or payload_item["mode"]!=0o600 or payload_item["nlink"]!=1
            or sha_file(payload)!=payload_item["sha256"]):raise GateFailure("payload_verification")
    gate=strict_json(PROV/"no_training_gate.json")
    exact_keys(gate,{"schema_version","status","terminal_status_if_seal_matches","model_scoring_authorized",
                     "k2_or_branch_training_authorized","stage_c_authorized","seal_sha256",
                     "scientific_preparation_entry_sha256"},"no_training_gate_verification")
    if (gate.get("schema_version")!="msae_independent_source_v9_no_training_gate_v1"
            or gate.get("status")!="pending_terminal_seal"
            or gate.get("terminal_status_if_seal_matches")!=seal.get("status")
            or gate.get("scientific_preparation_entry_sha256")!=sha_file(entry_path)
            or gate.get("seal_sha256")!=sha_file(seal_path) or gate.get("model_scoring_authorized") is not False
            or gate.get("k2_or_branch_training_authorized") is not False or gate.get("stage_c_authorized") is not False):
        raise GateFailure("no_training_gate_verification")


def main() -> None:
    global RAW_FILE_OPEN_COUNT,RAW_ACCESS_AUTHORIZED,DYNAMIC_PREFLIGHT_STARTED,ENTRY_PUBLICATION_STARTED
    p=argparse.ArgumentParser();p.add_argument("command",choices=("registry","baseline","authority","prepare","verify"));a=p.parse_args()
    if a.command=="registry":build_registry()
    elif a.command=="baseline":build_baseline()
    elif a.command=="authority":build_authority_manifest()
    elif a.command=="prepare":
        RAW_FILE_OPEN_COUNT=0;RAW_ACCESS_AUTHORIZED=False
        DYNAMIC_PREFLIGHT_STARTED=False;ENTRY_PUBLICATION_STARTED=False
        try:build_ready()
        except (GateFailure,OSError,UnicodeError,ValueError,KeyError,TypeError,json.JSONDecodeError) as error:
            code=str(error) if isinstance(error,GateFailure) else "boundary_"+type(error).__name__
            if RAW_FILE_OPEN_COUNT:
                retain_rejection(code)
            elif DYNAMIC_PREFLIGHT_STARTED and not ENTRY_PUBLICATION_STARTED:
                # Dynamic checks publish B0 themselves only after all three
                # evidence objects exist.  Here we may recover solely the
                # state-based final-without-temp publisher outcome; any other
                # exception is case C and must not synthesize missing evidence.
                final=PROV/"preflight_rejection.json"
                temporary=PROV/".preflight_rejection.json.building"
                if present_path(final) and not present_path(temporary):
                    verify_terminal()
                    return
            raise
    else:
        verify_terminal()

if __name__ == "__main__":
    main()
