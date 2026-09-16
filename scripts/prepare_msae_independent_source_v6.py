#!/usr/bin/env python3
"""Source-readiness builder for MSAE v6; standard-library and model-free."""
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
COMMIT = "5552572ac2c5aac1538e43edb7f7a8d2224f12de"
REPO = "https://github.com/UniversalDependencies/UD_English-ParTUT.git"
RAW = ROOT / "data/msae_independent_source_v6/raw" / COMMIT
PRIVATE = ROOT / "data/msae_independent_source_v6/private"
PROV = ROOT / "reports/provenance/msae_independent_source_v6"
QUARANTINES = {
    "data/atlas_v1/private/final.jsonl",
    "data/atlas_v1/private/final.records.jsonl",
    "data/atlas_v1/private/final.units.jsonl",
}
SOURCE_FILES = {
    "train": "en_partut-ud-train.conllu",
    "dev": "en_partut-ud-dev.conllu",
    "test": "en_partut-ud-test.conllu",
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
V6_PREFIX = "data/msae_independent_source_v6/"
V6_AUTHORITY = {
    "docs/plan-msae-independent-source-v5.md",
    "reports/provenance/msae_independent_source_v5/preacquisition_alias_screen.json",
    "reports/provenance/msae_independent_source_v5/historical_source_registry.json",
    "scripts/prepare_msae_independent_source_v5.py",
    "scripts/acquire_msae_independent_source_v5.py",
    "tests/test_prepare_msae_independent_source_v5.py",
    "configs/msae_independent_source_v5/acquisition.json",
    "docs/plan-msae-independent-source-v6.md",
    "reports/adversarial/msae_independent_source_v6_plan_review.md",
    "reports/provenance/msae_independent_source_v6/preacquisition_alias_screen.json",
    "reports/provenance/msae_independent_source_v6/historical_source_registry.json",
    "reports/provenance/msae_independent_source_v6/preacquisition_authority_manifest.json",
    "reports/provenance/msae_independent_source_v6/baseline_inventory.json",
    "scripts/prepare_msae_independent_source_v6.py",
    "scripts/acquire_msae_independent_source_v6.py",
    "tests/test_prepare_msae_independent_source_v6.py",
    "configs/msae_independent_source_v6/acquisition.json",
    "reports/verification/msae_independent_source_v6_source_free_checks.log",
    "reports/adversarial/msae_independent_source_v6_preacquisition_implementation_review.md",
    "reports/adversarial/msae_independent_source_v6_preacquisition_authority_review.md",
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
ALIASES = ("ud_english-partut", "english-partut", "en_partut", "partut", COMMIT, REPO.casefold())
FORBIDDEN_PROCESS_TOKENS=("torchrun","train_msae","msae_train","branch_training","run_branch_train",
                          "deepspeed","accelerate launch","nvidia-smi","cuda_visible_devices")

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


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_file_bytes(value: Any) -> bytes:
    return canonical_bytes(value) + b"\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def open_repo_file(path: Path) -> int:
    try:rel=path.relative_to(ROOT)
    except ValueError:
        return os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
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
    item={"path":rel,"state":"present","type":kind,"device":s.st_dev,"inode":s.st_ino,
          "mode":stat.S_IMODE(s.st_mode),"nlink":s.st_nlink,"size":s.st_size,"mtime_ns":s.st_mtime_ns}
    if hash_regular_final and kind=="regular":item["sha256"]=sha_regular_nofollow(path)
    if valid_payload_final and kind=="regular" and stat.S_IMODE(s.st_mode)==0o600 and s.st_nlink==1:
        item["sha256"]=sha_regular_nofollow(path)
    return item


def scientific_artifact_inventory() -> dict[str, Any]:
    entries=[]
    for name in SCIENTIFIC_ARTIFACT_NAMES:
        final=PROV/name;temporary=final.with_name("."+final.name+".building")
        entries.append(lstat_state(final,hash_regular_final=True))
        entries.append(lstat_state(temporary))
    return {"schema_version":"msae_independent_source_v6_scientific_artifact_inventory_v1",
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
    # The pre-plan registry has a frozen exact SHA-256 but predates the canonical writer by
    # one escaped-slash normalization; every create-once v6 final is canonical.
    if path.name!="historical_source_registry.json" and payload!=canonical_file_bytes(value):
        raise GateFailure("noncanonical_public_json")
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
    if (value["schema_version"] != "msae_independent_source_v6_process_snapshot_v1"
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
    expected_files = [SOURCE_FILES[role] for role in ("train", "dev", "test")] + ["README.md", "LICENSE.txt"]
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
    if (value.get("schema_version") != "msae_independent_source_v6_acquisition_v1"
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


def _predecessor_hashes() -> dict[str, str]:
    return {
        "docs/plan-msae-independent-source-v4-2.md": "ff93c8b2dc5de9e0920bb910126d3ef79d5ab941bbf9c61a47803fccf9d83ae4",
        "reports/adversarial/msae_independent_source_v4_2_plan_review.md": "9d065acea90371ffe51ba85d05923f2eb1a1fedfad719a0977fa8c610298f357",
        "scripts/prepare_msae_independent_source_v4_2.py": "f99037ac108aa193f26a0eab2a2b027625c9de2e64d49e37f16de9235ad704dc",
        "tests/test_prepare_msae_independent_source_v4_2.py": "91058a43bf8fccec566c79fed03b21daeef9119960511f4699d206af5a7a2e23",
        "reports/provenance/msae_independent_source_v4_2/rejection.json": "4599f41981a3169c53bf83c3a25ead86a4d05b8056fbeee8c44fc0a43101c477",
        "docs/plan-msae-independent-source-v5.md": "1c450895bf836b142bc46dced85afd4f109edd68a96f6e4e91dc5719f0b3fc6b",
        "scripts/prepare_msae_independent_source_v5.py": "f78aba1add310c6a76a05cac4ccc159b9c6aa924e888664d3a54f372e0ebb1e8",
        "scripts/acquire_msae_independent_source_v5.py": "6b5c78543c9530c98c24ce99f90ac1caff6ca496d111d8b25889ec448402d11f",
        "tests/test_prepare_msae_independent_source_v5.py": "f2cf4d0b58554d688fb4b601bcc739dc6749833d393b49e275178eedccdcac76",
        "configs/msae_independent_source_v5/acquisition.json": "6b53511b6d0976ada49a7f090b884d7faeb7db3afb55da9a2f593c369af3e66d",
        "reports/adversarial/msae_independent_source_v5_preacquisition_implementation_review.md": "b098b819f3cc122f4501ccf8465649e070fa46d83484bfc0bc86a283c14a33a2",
        "reports/provenance/msae_independent_source_v5/baseline_inventory.json": "51390650c9d3f7e80cc3810cc3be4b3eae23dc74358c611dca425fe98e31c7a3",
        "reports/provenance/msae_independent_source_v5/preacquisition_control_plane_rejection.json": "06bc319b12d763895d3d7c8038acb8c82b2ad965ef26d0c4cbcb05dd4a097136",
        "reports/adversarial/msae_independent_source_v5_preacquisition_control_plane_rejection_review.md": "6f83fe07fbb9b12dc7a75fbff2da2490300e0745e0c1fd15ad03b83fd8e5e347",
    }


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


def _finish_sentence(rows: list[Token], sent_id: str | None, index: int) -> Sentence:
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
    return Sentence(sent_id, tuple(rows), index)


def parse_conllu(path: Path) -> tuple[list[Sentence], dict[str, int]]:
    try:
        text = read_text_nofollow(path)
    except UnicodeError as e:
        raise GateFailure("invalid_utf8") from e
    rows: list[Token] = []
    sentences: list[Sentence] = []
    sent_id: str | None = None
    seen_ids: set[str] = set()
    counts = {"integer_tokens": 0, "multiword_rows": 0, "empty_node_rows": 0}
    def flush() -> None:
        nonlocal rows, sent_id
        if not rows and sent_id is None:
            return
        sentence = _finish_sentence(rows, sent_id, len(sentences))
        if sentence.sent_id in seen_ids:
            raise GateFailure("duplicate_sent_id")
        seen_ids.add(sentence.sent_id)
        sentences.append(sentence)
        rows = []
        sent_id = None
    for line in text.splitlines():
        if not line:
            flush(); continue
        if line.startswith("#"):
            if line.startswith("# newdoc id = "):
                raise GateFailure("unsupported_document_group")
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
    if not sentences:
        raise GateFailure("empty_source")
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


def split_key(sent_id: str, normalized: str) -> str:
    if "\0" in sent_id or "\0" in normalized:
        raise GateFailure("nul_split_key")
    return sha_bytes(canonical_bytes(["msae-independent-source-v6/C1C2", sent_id, normalized]))


def assign_split(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keyed = [(split_key(str(x["sent_id"]), str(x["normalized"])), str(x["sent_id"]), x) for x in rows]
    keyed.sort(key=lambda z: (z[0], z[1].encode("utf-8")))
    return [{**x, "split_key_sha256": h, "panel": "C1" if i % 2 == 0 else "C2", "zero_based_rank": i}
            for i, (h, _sid, x) in enumerate(keyed)]


def public_label(task: str, value: str) -> str:
    if task == "token_identity": return sha_bytes(("msae-v6/token\0" + value).encode())
    if task == "lemma_identity": return sha_bytes(("msae-v6/lemma\0" + value).encode())
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
    payload = read_bytes_nofollow(path)
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    is_text = b"\0" not in payload
    if is_text:
        try:
            decoder.decode(payload, final=True)
        except UnicodeDecodeError:
            is_text = False
    return sha_bytes(payload), is_text


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


def archive_members(path: Path) -> list[tuple[str, bytes]] | None:
    """Return one-level safe archive members, None when a valid archive exceeds frozen bounds."""
    limit = 1 << 30
    members: list[tuple[str, bytes]] = []
    suffixes = [x.lower() for x in path.suffixes]
    with path.open("rb") as probe_handle:
        probe = probe_handle.read(512)
    expected_kind = "zip" if path.suffix.lower() == ".zip" else "gzip" if path.suffix.lower() == ".gz" else "tar" if ".tar" in suffixes else None
    if expected_kind is None or _archive_kind(probe) != expected_kind:
        raise GateFailure("archive_magic_suffix_mismatch")
    try:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                infos = archive.infolist()
                if len(infos) > 100_000:
                    return None
                total = sum(item.file_size for item in infos)
                if total > limit or total > max(1, path.stat().st_size) * 20:
                    return None
                for item in infos:
                    mode = (item.external_attr >> 16) & 0o170000
                    if (item.is_dir() or item.flag_bits & 1 or not _safe_member_name(item.filename)
                            or mode not in (0, stat.S_IFREG)):
                        raise GateFailure("unsafe_archive_member")
                    members.append((item.filename, archive.read(item)))
        elif ".tar" in suffixes:
            with tarfile.open(path, "r:*") as archive:
                infos = archive.getmembers()
                if len(infos) > 100_000:
                    return None
                if any(not item.isfile() or not _safe_member_name(item.name) for item in infos):
                    raise GateFailure("unsafe_archive_member")
                total = sum(item.size for item in infos)
                if total > limit or total > max(1, path.stat().st_size) * 20:
                    return None
                for item in infos:
                    handle = archive.extractfile(item)
                    if handle is None:
                        raise GateFailure("unsafe_archive_member")
                    members.append((item.name, handle.read()))
        elif path.suffix.lower() == ".gz":
            with gzip.open(path, "rb") as handle:
                payload = handle.read(limit + 1)
            if len(payload) > limit or len(payload) > max(1, path.stat().st_size) * 20:
                return None
            members.append((path.stem, payload))
        else:
            raise GateFailure("unknown_archive")
    except (OSError, EOFError, tarfile.TarError, zipfile.BadZipFile) as error:
        raise GateFailure("invalid_archive") from error
    for name, payload in members:
        suffix = Path(name).suffix.lower()
        if suffix in {".zip", ".tar", ".gz", ".tgz"} or _archive_kind(payload) is not None:
            raise GateFailure("nested_archive")
        try:
            decoded = payload.decode("utf-8")
            text = "\0" not in decoded
        except UnicodeDecodeError:
            text = False
        if not text and not _opaque_member_matches_suffix(name, payload):
            raise GateFailure("unsupported_archive_member")
    return members


def inventory_one(path: Path, rel: str, quarantines: set[str]) -> dict[str, Any]:
    s = path.lstat()
    base = {"path": rel, "size": s.st_size, "mode": stat.S_IMODE(s.st_mode), "device": s.st_dev,
            "inode": s.st_ino, "nlink": s.st_nlink, "mtime_ns": s.st_mtime_ns}
    if rel in quarantines:
        return {**base, "sha256": None, "disposition": "quarantine", "adapter": "quarantine_lstat_only",
                "content_reads": 0, "extracted_unit_count": 0}
    digest, text = _file_hash_and_text(path)
    if path.suffix.lower() in {".zip", ".gz", ".tar"} or ".tar" in {x.lower() for x in path.suffixes}:
        members = archive_members(path)
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


def _walk_paths() -> Iterator[tuple[Path, str]]:
    for base, dirs, files in os.walk(ROOT):
        root = Path(base)
        relbase = root.relative_to(ROOT).as_posix()
        prefix = "" if relbase == "." else relbase + "/"
        retained = []
        for d in sorted(dirs):
            child = root / d
            child_rel = prefix + d
            child_stat = child.lstat()
            if stat.S_ISLNK(child_stat.st_mode) or not stat.S_ISDIR(child_stat.st_mode):
                raise GateFailure("special_paths")
            if child_rel.startswith(V6_PREFIX.rstrip("/")):
                if any(child.iterdir()):
                    raise GateFailure("preexisting_v6_namespace")
                continue
            if d == "__pycache__" or any((child_rel + "/").startswith(x) for x in GENERATED_PREFIXES):
                continue
            retained.append(d)
        dirs[:] = retained
        for name in sorted(files):
            p = root / name; rel = p.relative_to(ROOT).as_posix()
            if rel.startswith(".git/"): continue
            if rel.startswith(V6_PREFIX):
                raise GateFailure("preexisting_v6_namespace")
            yield p, rel


def inventory_repository() -> dict[str, Any]:
    paths = list(_walk_paths())
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
            elif rel.startswith(V6_PREFIX): item.update(disposition="v6_excluded", adapter="excluded", extracted_unit_count=0)
            elif rel in V6_AUTHORITY:
                item.update(disposition="v6_authority", adapter="authority", extracted_unit_count=0)
            entries.append(item)
    counts = collections.Counter(x["disposition"] for x in entries)
    if counts["terminal_unsupported"]: raise GateFailure("unsupported_files")
    return {"schema_version": "msae_independent_source_v6_baseline_inventory_v1",
            "baseline_head": "7e1a6fc7a26a870a4edcf29c96b7cdf3cdbd7faa",
            "entry_count": len(entries), "counts": dict(sorted(counts.items())),
            "quarantine_content_reads": 0, "entries": entries,
            "authority_expected_absent": sorted(V6_AUTHORITY - {x["path"] for x in entries}),
            "entries_sha256": sha_bytes(canonical_bytes(entries)), "status": "eligible"}


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


def _all_source() -> tuple[dict[str, list[Sentence]], dict[str, Any]]:
    roles: dict[str, list[Sentence]] = {}
    counts = {}
    for upstream, name in SOURCE_FILES.items():
        sentences, c = parse_conllu(RAW / name)
        role = "discovery" if upstream == "train" else "calibration" if upstream == "dev" else "test"
        roles[role] = sentences; counts[upstream] = {**c, "sentences": len(sentences), "sha256": sha_file(RAW/name)}
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
    report = {"schema_version": "msae_independent_source_v6_dedup_v1", "roles": {},
              "cross_partition_normalized_group_count": len(shared), "source_text_published": False}
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
    test = assign_split([{"sent_id": s.sent_id, "normalized": normalized_sentence(s), "sentence": s} for s in roles["test"]])
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
    return {"schema_version":"msae_independent_source_v6_support_v1","floor_distinct_utterances":20,
            "roles":result,"all_role_task_intersection":sorted(intersection),"status":"eligible" if passed else "ineligible"}


def _token_objects(sentence: Sentence) -> list[dict[str,Any]]:
    return [{"id":t.id,"form":t.form,"lemma":t.lemma,"upos":t.upos,"head":t.head,"deprel":t.deprel,"feats":t.feats} for t in sentence.tokens]


def _source_record_hash(sentence: Sentence) -> str:
    return sha_bytes(canonical_bytes(_token_objects(sentence)))


def _license() -> dict[str,Any]:
    lp=RAW/"LICENSE.txt";rp=RAW/"README.md"
    text=read_text_nofollow(lp).casefold();readme=read_text_nofollow(rp).casefold()
    contradictions = [term for term in ("all rights reserved", "no redistribution", "non-commercial use only")
                      if term in text or term in readme]
    ok=("creative commons attribution-sharealike 4.0" in text or "creativecommons.org/licenses/by-sa/4.0" in text or "cc by-sa 4.0" in text)
    ok=ok and ("cc by-sa 4.0" in readme or "creativecommons.org/licenses/by-sa/4.0" in readme)
    return {"schema_version":"msae_independent_source_v6_license_v1","license_id":"CC-BY-SA-4.0",
            "license_path":"LICENSE.txt","license_sha256":sha_file(lp),"readme_sha256":sha_file(rp),
            "license_url":"https://creativecommons.org/licenses/by-sa/4.0/",
            "obligations":["attribution","share_alike"],"raw_committed":False,"payload_committed":False,
            "contradiction_count":len(contradictions),
            "status":"eligible" if ok and not contradictions else "ineligible"}


def document_group_census() -> dict[str, Any]:
    count = 0
    files = {}
    for name in SOURCE_FILES.values():
        path = RAW/name
        local = 0
        for line in read_text_nofollow(path).splitlines():
            if line.startswith("# newdoc id = "):
                local += 1
        files[name] = local
        count += local
    return {"schema_version":"msae_independent_source_v6_document_group_census_v1",
            "newdoc_marker_count":count,"markers_by_file":dict(sorted(files.items())),
            "natural_unit":"sentence","document_speaker_cluster_inference_authorized":False,
            "status":"eligible" if count == 0 else "ineligible"}


def _source_family(inventory: dict[str,Any], raw_hashes:set[str]) -> dict[str,Any]:
    matches=[];whole=[];pathname_matches=[]
    expected_lines={
        "PLAN_ATTEMPT13.md":({280},"194294213047f528fddcc0374e4a1d4d5a185ce01f5d07eb13bce688f9820db8"),
        "PLAN_RELATIONAL_EDGE_V1.md":({221,412},"8d1d6c172da0d8302410659c8cfff948c59e1df0fbbe03d972adb5c148c49bcd"),
        "reports/provenance/relational_attention_edges_v1_discovery1_plan_snapshot.md":({132,316},"5a5e8fb6d1396632c700fa51386711d022a6107bb02572fa7d7c94790bdb0c51"),
    }
    for item in inventory["entries"]:
        rel=item["path"]
        folded_rel=rel.casefold()
        if any(alias in folded_rel for alias in ALIASES) or re.search(r"\bpartut\b",folded_rel):
            pathname_matches.append(rel)
        if item.get("sha256") in raw_hashes:whole.append(rel)
        if item["disposition"] not in {"text_scanned", "archive_scanned"}:continue
        p=ROOT/rel
        if item["disposition"] == "archive_scanned":
            members = archive_members(p)
            if members is None: raise GateFailure("archive_bound_drift")
            streams = [(name, io.StringIO(payload.decode("utf-8"))) for name,payload in members if _is_utf8(payload)]
        else:
            streams = [(None, io.StringIO(read_text_nofollow(p)))]
        for member_name, f in streams:
            try:
                for line_number,line in enumerate(f,start=1):
                    probe=line.casefold(); found=[a for a in ALIASES if a in probe]
                    if re.search(r"\bpartut\b",probe):found.append("partut")
                    if found:matches.append({"path":rel,"archive_member":member_name,"line":line_number,"aliases":sorted(set(found))})
            finally:
                f.close()
    observed={path:{item["line"] for item in matches if item["path"]==path and item["archive_member"] is None} for path in expected_lines}
    bound_files_ok=all(sha_file(ROOT/path)==digest and observed[path]==lines for path,(lines,digest) in expected_lines.items())
    unexpected=[x for x in matches if x["path"] not in expected_lines or x["archive_member"] is not None or x["line"] not in expected_lines[x["path"]][0]]
    unexpected_paths=[path for path in pathname_matches if path not in V6_AUTHORITY]
    eligible=not unexpected and not unexpected_paths and not whole and bound_files_ok
    return {"schema_version":"msae_independent_source_v6_source_family_v1","status":"eligible" if eligible else "ineligible",
            "disposition":"previously_considered_but_project_source_use_unseen","planning_or_authority_matches":matches,
            "unexpected_matches":unexpected,"pathname_matches":sorted(pathname_matches),
            "unexpected_pathname_matches":sorted(unexpected_paths),"bound_planning_occurrences_exact":bound_files_ok,
            "whole_file_digest_matches":whole}


PEDIGREE_URL = re.compile(rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{3,512}", re.I)
PEDIGREE_UD = re.compile(rb"(?<![A-Za-z0-9_])ud_[A-Za-z0-9_-]{2,128}(?![A-Za-z0-9_])", re.I)
PEDIGREE_JSON = re.compile(rb'"(?:source_repo|source_url|repo_url|repository|url|source_revision|source_commit|commit|revision|dataset|dataset_id|dataset_name|source_name|source_id|corpus|treebank)"\s*:\s*"([^"\\]{1,1024})"', re.I)
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
    # V6 inherits the byte-identical, never-entered v5 registry and therefore its frozen domain.
    return sha_bytes(b"msae-v5/pedigree\0" + value.encode("utf-8"))


def candidate_pedigree() -> dict[str, Any]:
    registry = strict_json(PROV / "historical_source_registry.json")
    historical = {item["identifier_sha256"] for item in registry["entries"]}
    allowed = {item["identifier_sha256"] for item in registry["allowed_framework_identifiers"]}
    identifiers = {normalize_pedigree(value.encode("utf-8")) for value in
                   (REPO, COMMIT, "UD_English-ParTUT", "en_partut", *SOURCE_FILES.values())}
    for name in ("README.md", "LICENSE.txt"):
        payload = read_bytes_nofollow(RAW/name)
        for item in re.finditer(rb"https?://\S+", payload, re.I):
            if len(item.group(0)) > 512:
                raise GateFailure("overlength_candidate_pedigree_identifier")
        key_prefix = re.compile(rb'"(?:source_repo|source_url|repo_url|repository|url|source_revision|source_commit|commit|revision|dataset|dataset_id|dataset_name|source_name|source_id|corpus|treebank)"\s*:\s*"', re.I)
        for item in key_prefix.finditer(payload):
            end = payload.find(b'"', item.end())
            if end < 0 or end-item.end()>1024 or b"\\" in payload[item.end():end]:
                raise GateFailure("ambiguous_candidate_pedigree_syntax")
        for item in re.finditer(rb"(?<![A-Za-z0-9_])ud_[A-Za-z0-9_-]+",payload,re.I):
            if len(item.group(0)) > 131:
                raise GateFailure("overlength_candidate_pedigree_identifier")
        for pattern in (PEDIGREE_URL, PEDIGREE_UD, PEDIGREE_JSON):
            for match in pattern.finditer(payload):
                identifiers.add(normalize_pedigree(match.group(1) if pattern is PEDIGREE_JSON else match.group(0)))
    hashes = sorted({pedigree_hash(value) for value in identifiers})
    blocking = sorted((set(hashes) & historical) - allowed)
    return {"schema_version": "msae_independent_source_v6_candidate_pedigree_v1",
            "registry_sha256": sha_file(PROV / "historical_source_registry.json"),
            "candidate_identifier_count": len(hashes), "candidate_identifier_sha256": hashes,
            "allowed_shared_identifier_sha256": sorted(set(hashes) & allowed),
            "blocking_identifier_sha256": blocking, "blocking_identifier_count": len(blocking),
            "source_prose_published": False, "status": "eligible" if not blocking else "ineligible"}


def _verify_predecessor_and_raw() -> dict[str, Any]:
    expected = {
        ROOT/"docs/plan-msae-independent-source-v6.md": "0bba4efcfea868b186f4051faa71d84382b33a8b1f8dc425ed595c7335b515cc",
        ROOT/"reports/adversarial/msae_independent_source_v6_plan_review.md": "e229b167d7cd9c2b93a34a654d57402af35be0533ae1ddbe9f0ae0d32cb7a6d7",
        ROOT/"reports/provenance/msae_independent_source_v6/preacquisition_alias_screen.json": "c0c17ed89e19b3af611bae43e73095ca4acb4d0a61a01f7c3ef8979cbe2fbd7d",
        ROOT/"reports/provenance/msae_independent_source_v6/historical_source_registry.json": "484a2b8c13798924c159d0e1bf7fbc90d19010111f89b08e7ddb7ceb6780b83f",
        **{ROOT/path:digest for path,digest in _predecessor_hashes().items()},
    }
    if any(sha_file(path) != digest for path,digest in expected.items()):
        raise GateFailure("predecessor_drift")
    required_public=(
        PROV/"baseline_inventory.json",
        PROV/"preacquisition_authority_manifest.json",
        ROOT/"reports/adversarial/msae_independent_source_v6_preacquisition_authority_review.md",
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
    names=[*SOURCE_FILES.values(),"README.md","LICENSE.txt"]
    config=validate_acquisition_config(ROOT/"configs/msae_independent_source_v6/acquisition.json")
    environment=acquisition.get("environment",{})
    clone_dir=acquisition.get("clone_dir")
    empty_home=acquisition.get("empty_home")
    expected_clone=[clone_dir if item=="${CLONE_DIR}" else item for item in config["clone_argv"]]
    expected_checkout=[clone_dir if item=="${CLONE_DIR}" else item for item in config["checkout_argv"]]
    expected_environment={key:(empty_home if value=="${EMPTY_HOME}" else value) for key,value in config["environment"].items()}
    if (entry.get("schema_version")!="msae_independent_source_v6_source_acquisition_entry_v1"
            or entry.get("status")!="entered"
            or entry.get("authority_manifest_sha256")!=sha_file(PROV/"preacquisition_authority_manifest.json")
            or entry.get("authority_review_sha256")!=authority["authority_review_sha256"]
            or entry.get("baseline_inventory_sha256")!=sha_file(PROV/"baseline_inventory.json")
            or entry.get("config_sha256")!=sha_file(ROOT/"configs/msae_independent_source_v6/acquisition.json")
            or entry.get("runner_sha256")!=sha_file(ROOT/"scripts/acquire_msae_independent_source_v6.py")
            or entry.get("source_repo")!=REPO or entry.get("source_commit")!=COMMIT or entry.get("files")!=names
            or entry.get("subprocesses_started")!=0
            or entry.get("model_scoring_authorized") is not False
            or entry.get("k2_or_branch_training_authorized") is not False
            or entry.get("stage_c_authorized") is not False):
        raise GateFailure("source_acquisition_entry_drift")
    if (acquisition.get("schema_version")!="msae_independent_source_v6_source_acquisition_v1"
            or acquisition.get("source_repo") != REPO or acquisition.get("source_commit") != COMMIT
            or acquisition.get("resolved_head") != COMMIT
            or not re.fullmatch(r"[0-9a-f]{40}",str(acquisition.get("tree_object_sha1","")))
            or acquisition.get("tree_verified_from_ls_tree") is not True
            or acquisition.get("authority_manifest_sha256") != sha_file(PROV/"preacquisition_authority_manifest.json")
            or acquisition.get("authority_review_sha256") != authority["authority_review_sha256"]
            or acquisition.get("source_acquisition_entry_sha256") != sha_file(PROV/"source_acquisition_entry.json")
            or acquisition.get("acquisition_gate_argument") != authority["authority_review_sha256"]
            or acquisition.get("config_sha256") != sha_file(ROOT/"configs/msae_independent_source_v6/acquisition.json")
            or acquisition.get("executed_clone_argv") != expected_clone
            or acquisition.get("executed_checkout_argv") != expected_checkout
            or environment != expected_environment or acquisition.get("proxy_variables_present") != []
            or acquisition.get("sparse_checkout_sha256") != sha_bytes(("\n".join("/"+name for name in names)+"\n").encode("utf-8"))
            or acquisition.get("tree_paths") != names
            or acquisition.get("runner_sha256") != sha_file(ROOT/"scripts/acquire_msae_independent_source_v6.py")
            or acquisition.get("source_content_printed") is not False
            or acquisition.get("network_access") != "git_clone_and_checkout_only"
            or acquisition.get("model_operations") != 0 or acquisition.get("gpu_queries") != 0
            or acquisition.get("training_runs") != 0
            or set(acquisition.get("files",{})) != set(names)):
        raise GateFailure("source_acquisition_drift")
    statuses=acquisition.get("command_exit_status",{})
    if statuses!={"ignore_raw":0,"ignore_private":0,"clone":0,"checkout":0,"head":0,"tree":0,"ls_tree":0,"hash_object_count":5}:
        raise GateFailure("source_acquisition_exit_status")
    commands=acquisition.get("commands",[])
    expected_command_names=["ignore_raw","ignore_private","clone","checkout","head","tree","ls_tree",*["hash_object:"+name for name in names]]
    expected_command_argv=[
        [*config["ignore_argv"][:-1],"data/msae_independent_source_v6/raw/sentinel"],
        [*config["ignore_argv"][:-1],"data/msae_independent_source_v6/private/sentinel"],
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
    if ([item.get("path") for item in ignores] != ["data/msae_independent_source_v6/raw/sentinel","data/msae_independent_source_v6/private/sentinel"]
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
    current_paths={rel for _path,rel in _walk_paths_allow_v6(include_v6=True)}
    additions=current_paths-baseline_paths
    allowed_added=allowed_added or set()
    unexpected={rel for rel in additions if rel not in allowed_added and not any(rel.startswith(prefix) for prefix in allowed_prefixes)}
    if unexpected:
        raise GateFailure("history_structural_addition")
    for item in inventory["entries"]:
        if item["disposition"] not in {"text_scanned", "archive_scanned", "binary_unscanned", "v6_authority", "quarantine"}:
            continue
        path=ROOT/item["path"]
        s=path.lstat()
        if (not stat.S_ISREG(s.st_mode) or s.st_size!=item["size"] or s.st_dev!=item["device"]
                or s.st_ino!=item["inode"] or s.st_mtime_ns!=item["mtime_ns"]
                or stat.S_IMODE(s.st_mode)!=item["mode"] or s.st_nlink!=item["nlink"]):
            raise GateFailure("history_snapshot_drift")
        if item["disposition"] != "quarantine" and sha_file(path) != item["sha256"]:
            raise GateFailure("history_snapshot_hash_drift")
        if item["disposition"] == "binary_unscanned":
            _digest,is_text=_file_hash_and_text(path)
            if is_text:
                raise GateFailure("binary_history_classification_drift")


def verify_pre_payload_v6_namespace() -> None:
    fds=[]
    try:
        v6fd=open_repo_dir(RAW.parent.parent);fds.append(v6fd)
        rawrootfd=os.open("raw",os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0),dir_fd=v6fd);fds.append(rawrootfd)
        commitfd=os.open(COMMIT,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0),dir_fd=rawrootfd);fds.append(commitfd)
        for fd,mode in ((v6fd,0o700),(rawrootfd,0o700),(commitfd,0o555)):
            if stat.S_IMODE(os.fstat(fd).st_mode)!=mode:raise GateFailure("v6_namespace_directory_drift")
        if sorted(os.listdir(v6fd)) != ["raw"]:raise GateFailure("v6_namespace_extra_path")
        if sorted(os.listdir(rawrootfd)) != [COMMIT]:raise GateFailure("v6_raw_parent_extra_path")
        expected=sorted([*SOURCE_FILES.values(),"README.md","LICENSE.txt"])
        if sorted(os.listdir(commitfd)) != expected:raise GateFailure("raw_file_set_drift")
        for name in expected:
            fd=os.open(name,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0),dir_fd=commitfd)
            try:s=os.fstat(fd)
            finally:os.close(fd)
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
              "command_sha256":sha_bytes(b"msae-v6/process\0"+raw),"forbidden_codes":codes}
        entries.append(item)
        if codes:matches.append(item)
    return {"schema_version":"msae_independent_source_v6_process_snapshot_v1",
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
    for item in inventory["training_root_entries"]:
        path=ROOT/item["path"];st=path.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_size!=item["size"] or st.st_ino!=item["inode"]
                or st.st_mtime_ns!=item["mtime_ns"] or (item["sha256"] is not None and sha_file(path)!=item["sha256"])):
            raise GateFailure("training_root_drift")
    current=[]
    for path,rel in _walk_paths_allow_v6():
        folded=rel.casefold();name=Path(folded).name
        if (folded.startswith("results/") or "checkpoint" in folded or name=="train_metrics.jsonl"
                or (folded.startswith("pilot_runs/") and Path(folded).suffix in {".pt",".pth",".ckpt",".safetensors"})):
            st=path.lstat()
            if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
                raise GateFailure("training_root_special_path")
            current.append({"path":rel,"size":st.st_size,"mode":stat.S_IMODE(st.st_mode),"inode":st.st_ino,
                            "mtime_ns":st.st_mtime_ns,"sha256":sha_file(path),
                            "disposition":next((x["disposition"] for x in inventory["training_root_entries"] if x["path"]==rel),"new")})
    current.sort(key=lambda item:item["path"])
    if current != inventory["training_root_entries"]:
        raise GateFailure("training_root_delta")


def _walk_paths_allow_v6(include_v6: bool = False) -> Iterator[tuple[Path,str]]:
    for base,dirs,files in os.walk(ROOT,followlinks=False):
        root=Path(base);relbase=root.relative_to(ROOT).as_posix();prefix="" if relbase=="." else relbase+"/"
        retained=[]
        for d in sorted(dirs):
            rel=prefix+d;st=(root/d).lstat()
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                raise GateFailure("special_paths")
            if d=="__pycache__" or any((rel+"/").startswith(x) for x in GENERATED_PREFIXES) or (not include_v6 and rel.startswith(V6_PREFIX.rstrip("/"))):
                continue
            retained.append(d)
        dirs[:]=retained
        for name in sorted(files):
            path=root/name;rel=path.relative_to(ROOT).as_posix()
            if not rel.startswith(".git/"):
                yield path,rel


def _authority_inputs() -> dict[str, str]:
    paths = [
        "docs/plan-msae-independent-source-v6.md",
        "reports/adversarial/msae_independent_source_v6_plan_review.md",
        "reports/provenance/msae_independent_source_v6/preacquisition_alias_screen.json",
        "reports/provenance/msae_independent_source_v6/historical_source_registry.json",
        "scripts/prepare_msae_independent_source_v6.py",
        "scripts/acquire_msae_independent_source_v6.py",
        "tests/test_prepare_msae_independent_source_v6.py",
        "configs/msae_independent_source_v6/acquisition.json",
        "reports/verification/msae_independent_source_v6_source_free_checks.log",
        "reports/adversarial/msae_independent_source_v6_preacquisition_implementation_review.md",
    ]
    return {path:sha_file(ROOT/path) for path in paths}


def implementation_review_sha() -> str:
    review=ROOT/"reports/adversarial/msae_independent_source_v6_preacquisition_implementation_review.md"
    required=[
        sha_file(ROOT/"docs/plan-msae-independent-source-v6.md"),
        sha_file(ROOT/"reports/adversarial/msae_independent_source_v6_plan_review.md"),
        sha_file(PROV/"preacquisition_alias_screen.json"),
        sha_file(PROV/"historical_source_registry.json"),
        sha_file(Path(__file__)),
        sha_file(ROOT/"scripts/acquire_msae_independent_source_v6.py"),
        sha_file(ROOT/"tests/test_prepare_msae_independent_source_v6.py"),
        sha_file(ROOT/"configs/msae_independent_source_v6/acquisition.json"),
        sha_file(ROOT/"reports/verification/msae_independent_source_v6_source_free_checks.log"),
    ]
    return _require_ship_review(review,required)


def build_authority_manifest() -> None:
    path=PROV/"preacquisition_authority_manifest.json"
    if present_path(path):
        raise GateFailure("authority_manifest_already_exists")
    authority_review=ROOT/"reports/adversarial/msae_independent_source_v6_preacquisition_authority_review.md"
    if present_path(authority_review):
        raise GateFailure("authority_review_preexists_manifest")
    baseline=strict_json(PROV/"baseline_inventory.json")
    _verify_history_snapshot(
        baseline,
        allowed_added={"reports/provenance/msae_independent_source_v6/baseline_inventory.json"},
    )
    verify_training_roots(baseline)
    implementation_review_sha();inputs=_authority_inputs()
    review_path=ROOT/"reports/adversarial/msae_independent_source_v6_preacquisition_implementation_review.md"
    _require_ship_review(review_path,[inputs["scripts/prepare_msae_independent_source_v6.py"],
                                      inputs["tests/test_prepare_msae_independent_source_v6.py"],
                                      inputs["configs/msae_independent_source_v6/acquisition.json"],
                                      inputs["reports/verification/msae_independent_source_v6_source_free_checks.log"]])
    snap=baseline["process_snapshot"]
    if snap.get("status")!="eligible" or snap.get("forbidden_identity_count")!=0:
        raise GateFailure("baseline_process_ineligible")
    value={"schema_version":"msae_independent_source_v6_preacquisition_authority_v1",
           "status":"approved_for_exact_source_acquisition","artifact_sha256":inputs,
           "predecessor_sha256":_predecessor_hashes(),
           "baseline_inventory_sha256":sha_file(PROV/"baseline_inventory.json"),
           "baseline_entries_sha256":baseline["entries_sha256"],
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
    expected_inputs=_authority_inputs()
    exact_keys(manifest,{"schema_version","status","artifact_sha256","predecessor_sha256",
        "baseline_inventory_sha256","baseline_entries_sha256","baseline_process_snapshot_sha256",
        "baseline_forbidden_identity_count","training_root_entries_sha256","quarantine_content_reads",
        "authority_review_required","source_acquisition_authorized","model_scoring_authorized",
        "k2_or_branch_training_authorized","model_operations_initiated","gpu_queries_initiated",
        "training_runs_initiated"},"authority_manifest_drift")
    if (manifest.get("schema_version")!="msae_independent_source_v6_preacquisition_authority_v1"
            or manifest.get("status")!="approved_for_exact_source_acquisition"
            or manifest.get("artifact_sha256")!=expected_inputs
            or manifest.get("predecessor_sha256")!=_predecessor_hashes()
            or manifest.get("baseline_inventory_sha256")!=sha_file(PROV/"baseline_inventory.json")
            or manifest.get("baseline_entries_sha256")!=baseline.get("entries_sha256")
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
    review_path=ROOT/"reports/adversarial/msae_independent_source_v6_preacquisition_authority_review.md"
    review_sha=_require_ship_review(review_path,[sha_file(manifest_path),sha_file(PROV/"baseline_inventory.json")])
    return {**manifest,"authority_review_sha256":review_sha}


def build_baseline() -> None:
    if sys.version_info[:3] != (3,12,3) or unicodedata.unidata_version != "15.0.0":raise GateFailure("runtime_drift")
    if validate_static_contract(Path(__file__)):
        raise GateFailure("static_contract")
    validate_acquisition_config(ROOT/"configs/msae_independent_source_v6/acquisition.json")
    implementation_review_sha()
    inv=inventory_repository()
    inv["process_snapshot"]=process_snapshot()
    if inv["process_snapshot"]["status"]!="eligible":raise GateFailure("forbidden_baseline_process")
    inv["training_root_entries"]=_training_entries(inv)
    inv["training_root_entries_sha256"]=sha_bytes(canonical_bytes(inv["training_root_entries"]))
    write_json(PROV/"baseline_inventory.json",inv)


def require_frozen_runtime() -> None:
    if sys.version_info[:3] != (3,12,3) or unicodedata.unidata_version != "15.0.0":
        raise GateFailure("runtime_drift")


def build_ready() -> None:
    require_frozen_runtime()
    if validate_static_contract(Path(__file__)):
        raise GateFailure("static_contract")
    terminal_paths=[PROV/name for name in ("rejection.json","seal.json","no_training_gate.json")]
    terminal_paths += [path.with_name("."+path.name+".building") for path in terminal_paths]
    if any(present_path(path) for path in terminal_paths):
        raise GateFailure("terminal_outcome_already_exists")
    verify_pre_payload_v6_namespace()
    _verify_predecessor_and_raw()
    inv=strict_json(PROV/"baseline_inventory.json")
    raw_additions={f"data/msae_independent_source_v6/raw/{COMMIT}/{name}"
                   for name in [*SOURCE_FILES.values(),"README.md","LICENSE.txt"]}
    _verify_history_snapshot(
        inv,
        allowed_added=raw_additions|{
            "reports/provenance/msae_independent_source_v6/baseline_inventory.json",
            "reports/provenance/msae_independent_source_v6/preacquisition_authority_manifest.json",
            "reports/adversarial/msae_independent_source_v6_preacquisition_authority_review.md",
            "reports/provenance/msae_independent_source_v6/source_acquisition_entry.json",
            "reports/provenance/msae_independent_source_v6/source_acquisition.json",
        },
    )
    verify_training_roots(inv)
    now=process_snapshot()
    if now["status"]!="eligible":raise GateFailure("forbidden_prepare_process")
    census=document_group_census();write_json(PROV/"document_group_census.json",census)
    if census["status"]!="eligible":raise GateFailure("unsupported_document_group")
    roles,source_counts=_all_source()
    source_manifest={"schema_version":"msae_independent_source_v6_source_manifest_v1","source_commit":COMMIT,
                     "partitions":source_counts,"source_text_published":False}
    write_json(PROV/"source_manifest.json",source_manifest)
    lic=_license(); write_json(PROV/"license.json",lic)
    if lic["status"]!="eligible":raise GateFailure("license_ineligible")
    raw_hashes={sha_file(RAW/name) for name in [*SOURCE_FILES.values(),"README.md","LICENSE.txt"]}
    fam=_source_family(inv,raw_hashes);write_json(PROV/"source_family.json",fam)
    if fam["status"]!="eligible":raise GateFailure("source_family_ineligible")
    pedigree=candidate_pedigree();write_json(PROV/"candidate_pedigree.json",pedigree)
    if pedigree["status"]!="eligible":raise GateFailure("candidate_pedigree_ineligible")
    roles,dedup=deduplicate_roles(roles);write_json(PROV/"dedup.json",dedup)
    rows=_source_rows(roles)
    cross=_role_overlap(rows);write_json(PROV/"cross_role_overlap.json",{"schema_version":"msae_independent_source_v6_cross_role_overlap_v1","blocking_collision_count":len(cross),"blocking_collisions":cross,"status":"eligible" if not cross else "ineligible"})
    if cross:raise GateFailure("cross_role_overlap")
    hits,unit_count,adapter_census=_history_overlap(rows,inv)
    inv["entries_sha256"]=sha_bytes(canonical_bytes(inv["entries"]));write_json(PROV/"history_manifest.json",inv)
    overlap={"schema_version":"msae_independent_source_v6_history_overlap_v1","baseline_inventory_sha256":sha_file(PROV/"baseline_inventory.json"),"history_entries_sha256":inv["entries_sha256"],"history_unit_count":unit_count,"history_adapter_census":adapter_census,"candidate_utterance_count":sum(map(len,rows.values())),"blocking_collision_count":len(hits),"blocking_collisions":hits,"quarantine_content_reads":0,"opaque_binary_history_count":inv["counts"].get("binary_unscanned",0),"status":"eligible" if not hits else "ineligible"}
    write_json(PROV/"history_overlap.json",overlap)
    if hits:raise GateFailure("history_overlap")
    support=_support(rows);support["unsupported_tasks"]=["neutral_prefix_offset","entity_binary","entity_type","source_genre"];write_json(PROV/"support.json",support)
    if support["status"]!="eligible":raise GateFailure("support_ineligible")
    role_manifest={"schema_version":"msae_independent_source_v6_role_manifest_v1","source_commit":COMMIT,"roles":{}}
    for role,upstream in (("discovery","train"),("calibration","dev")):
        vals=rows[role];role_manifest["roles"][role]={"upstream_partition":upstream,"record_count":len(vals),"entries":[{"zero_based_rank":i,"sent_id":x["sent_id"],"source_record_sha256":_source_record_hash(x["sentence"])} for i,x in enumerate(vals)]}
    write_json(PROV/"role_manifest.json",role_manifest)
    test_rows=assign_split([{"sent_id":s.sent_id,"normalized":normalized_sentence(s),"sentence":s} for s in roles["test"]])
    split={"schema_version":"msae_independent_source_v6_split_manifest_v1","source_commit":COMMIT,"upstream_partition":"test","split_algorithm":"sha256-canonical-json-array-v1-even-C1-odd-C2","record_count":len(test_rows),"C1_count":sum(x["panel"]=="C1" for x in test_rows),"C2_count":sum(x["panel"]=="C2" for x in test_rows),"entries":[{"sent_id":x["sent_id"],"panel":x["panel"],"zero_based_rank":x["zero_based_rank"],"split_key_sha256":x["split_key_sha256"],"source_record_sha256":_source_record_hash(x["sentence"])} for x in test_rows]}
    write_json(PROV/"split_manifest.json",split)
    payload_records=({"schema_version":"msae_independent_source_v6_payload_v1","source_repo":REPO,"source_commit":COMMIT,"upstream_partition":"test","panel":x["panel"],"split_key_sha256":x["split_key_sha256"],"sent_id":x["sent_id"],"tokens":_token_objects(x["sentence"])} for x in test_rows)
    payload=publish_private_jsonl(PRIVATE,"blind_payload.jsonl",payload_records);ps=payload.lstat()
    post=process_snapshot()
    if post["status"]!="eligible":raise GateFailure("forbidden_final_process")
    verify_training_roots(inv)
    write_json(PROV/"post_process_snapshot.json",post)
    artifact_names=["baseline_inventory.json","source_acquisition_entry.json","source_acquisition.json","source_family.json","candidate_pedigree.json","license.json","document_group_census.json","source_manifest.json","dedup.json","history_manifest.json","history_overlap.json","cross_role_overlap.json","support.json","role_manifest.json","split_manifest.json","post_process_snapshot.json","preacquisition_alias_screen.json","historical_source_registry.json","preacquisition_authority_manifest.json"]
    bindings={name:sha_file(PROV/name) for name in artifact_names}
    plan_sha=sha_file(ROOT/"docs/plan-msae-independent-source-v6.md");review_sha=sha_file(ROOT/"reports/adversarial/msae_independent_source_v6_plan_review.md")
    seal={"schema_version":"msae_independent_source_v6_seal_v1","status":"independent_source_ready_for_future_prescore_protocol","source_status":"previously_considered_but_project_source_use_unseen","plan_sha256":plan_sha,"plan_review_sha256":review_sha,"program_sha256":sha_file(Path(__file__)),"acquisition_runner_sha256":sha_file(ROOT/'scripts/acquire_msae_independent_source_v6.py'),"test_sha256":sha_file(ROOT/'tests/test_prepare_msae_independent_source_v6.py'),"artifact_sha256":bindings,"payload":{"path":"data/msae_independent_source_v6/private/blind_payload.jsonl","sha256":sha_file(payload),"size":ps.st_size,"record_count":len(test_rows),"mode":stat.S_IMODE(ps.st_mode),"nlink":ps.st_nlink},"model_operations_initiated_by_builder":0,"gpu_queries_initiated_by_builder":0,"training_runs_initiated_by_builder":0,"external_observation_scope":"baseline_and_terminal_proc_snapshots_plus_training_root_diff","unsupported_tasks":["neutral_prefix_offset","entity_binary","entity_type","source_genre"],"opaque_binary_history_excluded":True,"document_speaker_cluster_inference_authorized":False}
    seal_sha=sha_bytes(canonical_file_bytes(seal))
    write_json(PROV/"no_training_gate.json",{"schema_version":"msae_independent_source_v6_no_training_gate_v1","status":"pending_terminal_seal","terminal_status_if_seal_matches":"independent_source_ready_for_future_prescore_protocol","model_scoring_authorized":False,"k2_or_branch_training_authorized":False,"stage_c_authorized":False,"seal_sha256":seal_sha})
    write_json(PROV/"seal.json",seal)


def retain_rejection(code: str) -> None:
    if present_path(PROV/"seal.json"):
        return
    terminal=process_snapshot();training_status="unavailable"
    if present_path(PROV/"baseline_inventory.json"):
        baseline=strict_json(PROV/"baseline_inventory.json")
        try:
            verify_training_roots(baseline);training_status="unchanged"
        except GateFailure:
            training_status="changed"
    public_inventory=scientific_artifact_inventory();private_state=payload_state();final_state=private_state[0]
    payload_created=(final_state.get("type")=="regular" and final_state.get("mode")==0o600
                     and final_state.get("nlink")==1 and "sha256" in final_state)
    payload_binding=({key:final_state[key] for key in ("path","sha256","size","mode","nlink")}
                     if payload_created else None)
    value={"schema_version":"msae_independent_source_v6_rejection_v1","status":"rejected","failure_code":code,
           "scientific_artifact_inventory":public_inventory,"payload_state":private_state,
           "payload_created":payload_created,"payload":payload_binding,"source_content_reported":False,
           "model_operations_initiated_by_builder":0,"gpu_queries_initiated_by_builder":0,
           "training_runs_initiated_by_builder":0,"terminal_process_snapshot":terminal,
           "training_root_status":training_status,"model_scoring_authorized":False,
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
        "training_root_entries","training_root_entries_sha256"},code)
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
                or item.get("disposition") not in {"text_scanned","archive_scanned","binary_unscanned","v6_authority","quarantine"}
                or item.get("adapter") not in {"physical_lines","conllu_sentences","safe_archive_members",
                                               "opaque_archive_outside_bounds","opaque_binary","authority",
                                               "quarantine_lstat_only"}
                or (item["disposition"]=="quarantine") != (item["sha256"] is None)
                or (item["sha256"] is not None and not _is_sha(item["sha256"]))):raise GateFailure(code)
        if "hardlink_aliases" in item and (not isinstance(item["hardlink_aliases"],list)
                or item["hardlink_aliases"]!=sorted(item["hardlink_aliases"])):raise GateFailure(code)
        if "archive_members_sha256" in item and not _is_sha(item["archive_members_sha256"]):raise GateFailure(code)
    derived=dict(sorted(collections.Counter(item["disposition"] for item in entries).items()))
    training=value["training_root_entries"]
    if (value["schema_version"]!="msae_independent_source_v6_baseline_inventory_v1"
            or value["baseline_head"]!="7e1a6fc7a26a870a4edcf29c96b7cdf3cdbd7faa"
            or value["entry_count"]!=len(entries) or value["counts"]!=derived
            or value["quarantine_content_reads"]!=0 or value["status"]!="eligible"
            or value["entries_sha256"]!=sha_bytes(canonical_bytes(entries))
            or not isinstance(value["authority_expected_absent"],list)
            or value["authority_expected_absent"]!=sorted(set(value["authority_expected_absent"]))
            or not isinstance(training,list)
            or any(not isinstance(item,dict) or set(item)!={"path","size","mode","inode","mtime_ns","sha256","disposition"}
                   for item in training)
            or value["training_root_entries_sha256"]!=sha_bytes(canonical_bytes(training))):raise GateFailure(code)
    verify_process_snapshot_schema(value["process_snapshot"],code)
    if value["process_snapshot"]["status"]!="eligible" or value["process_snapshot"]["forbidden_identity_count"]!=0:
        raise GateFailure(code)


def validate_scientific_artifacts() -> None:
    code="scientific_artifact_reconstruction"
    baseline=strict_json(PROV/"baseline_inventory.json");history=strict_json(PROV/"history_manifest.json")
    _validate_inventory_artifact(baseline,code);_validate_inventory_artifact(history,code)
    by_path={item["path"]:item for item in baseline["entries"]}
    history_by_path={item["path"]:item for item in history["entries"]}
    if set(by_path)!=set(history_by_path):raise GateFailure(code)
    for path,item in by_path.items():
        other=history_by_path[path]
        if any(item.get(key)!=other.get(key) for key in set(item)|set(other) if key!="extracted_unit_count"):
            raise GateFailure(code)

    census=exact_keys(strict_json(PROV/"document_group_census.json"),
        {"schema_version","newdoc_marker_count","markers_by_file","natural_unit",
         "document_speaker_cluster_inference_authorized","status"},code)
    if (census["schema_version"]!="msae_independent_source_v6_document_group_census_v1"
            or set(census["markers_by_file"])!=set(SOURCE_FILES.values())
            or any(not _is_count(value) for value in census["markers_by_file"].values())
            or census["newdoc_marker_count"]!=sum(census["markers_by_file"].values())
            or census["newdoc_marker_count"]!=0 or census["natural_unit"]!="sentence"
            or census["document_speaker_cluster_inference_authorized"] is not False or census["status"]!="eligible"):
        raise GateFailure(code)

    source=exact_keys(strict_json(PROV/"source_manifest.json"),
        {"schema_version","source_commit","partitions","source_text_published"},code)
    if set(source["partitions"])!={"train","dev","test"}:raise GateFailure(code)
    for name,item in source["partitions"].items():
        exact_keys(item,{"integer_tokens","multiword_rows","empty_node_rows","sentences","sha256"},code)
        if any(not _is_count(item[key]) for key in ("integer_tokens","multiword_rows","empty_node_rows","sentences")) or not _is_sha(item["sha256"]):raise GateFailure(code)
    if (source["schema_version"]!="msae_independent_source_v6_source_manifest_v1"
            or source["source_commit"]!=COMMIT or source["source_text_published"] is not False):raise GateFailure(code)

    license_value=exact_keys(strict_json(PROV/"license.json"),
        {"schema_version","license_id","license_path","license_sha256","readme_sha256","license_url",
         "obligations","raw_committed","payload_committed","contradiction_count","status"},code)
    if (license_value["schema_version"]!="msae_independent_source_v6_license_v1"
            or license_value["license_id"]!="CC-BY-SA-4.0" or license_value["license_path"]!="LICENSE.txt"
            or license_value["license_sha256"]!=sha_file(RAW/"LICENSE.txt")
            or license_value["readme_sha256"]!=sha_file(RAW/"README.md")
            or license_value["license_url"]!="https://creativecommons.org/licenses/by-sa/4.0/"
            or license_value["obligations"]!=["attribution","share_alike"]
            or license_value["raw_committed"] is not False or license_value["payload_committed"] is not False
            or license_value["contradiction_count"]!=0 or license_value["status"]!="eligible"):raise GateFailure(code)

    family=exact_keys(strict_json(PROV/"source_family.json"),
        {"schema_version","status","disposition","planning_or_authority_matches","unexpected_matches",
         "pathname_matches","unexpected_pathname_matches","bound_planning_occurrences_exact",
         "whole_file_digest_matches"},code)
    for item in family["planning_or_authority_matches"]:
        exact_keys(item,{"path","archive_member","line","aliases"},code)
        if (not isinstance(item["path"],str) or item["archive_member"] is not None
                or not _is_count(item["line"]) or item["line"]<1 or not isinstance(item["aliases"],list)
                or item["aliases"]!=sorted(set(item["aliases"]))):raise GateFailure(code)
    if (family["schema_version"]!="msae_independent_source_v6_source_family_v1" or family["status"]!="eligible"
            or family["disposition"]!="previously_considered_but_project_source_use_unseen"
            or family["unexpected_matches"]!=[] or family["unexpected_pathname_matches"]!=[]
            or family["whole_file_digest_matches"]!=[] or family["bound_planning_occurrences_exact"] is not True
            or family["pathname_matches"]!=sorted(family["pathname_matches"])):raise GateFailure(code)

    pedigree=exact_keys(strict_json(PROV/"candidate_pedigree.json"),
        {"schema_version","registry_sha256","candidate_identifier_count","candidate_identifier_sha256",
         "allowed_shared_identifier_sha256","blocking_identifier_sha256","blocking_identifier_count",
         "source_prose_published","status"},code)
    for key in ("candidate_identifier_sha256","allowed_shared_identifier_sha256","blocking_identifier_sha256"):
        if pedigree[key]!=sorted(set(pedigree[key])) or any(not _is_sha(item) for item in pedigree[key]):raise GateFailure(code)
    if (pedigree["schema_version"]!="msae_independent_source_v6_candidate_pedigree_v1"
            or pedigree["registry_sha256"]!=sha_file(PROV/"historical_source_registry.json")
            or pedigree["candidate_identifier_count"]!=len(pedigree["candidate_identifier_sha256"])
            or not set(pedigree["allowed_shared_identifier_sha256"])<=set(pedigree["candidate_identifier_sha256"])
            or pedigree["blocking_identifier_count"]!=len(pedigree["blocking_identifier_sha256"])
            or pedigree["blocking_identifier_count"]!=0 or pedigree["source_prose_published"] is not False
            or pedigree["status"]!="eligible"):raise GateFailure(code)

    dedup=exact_keys(strict_json(PROV/"dedup.json"),
        {"schema_version","roles","cross_partition_normalized_group_count","source_text_published"},code)
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
    if (dedup["schema_version"]!="msae_independent_source_v6_dedup_v1"
            or not _is_count(dedup["cross_partition_normalized_group_count"])
            or dedup["source_text_published"] is not False):raise GateFailure(code)

    cross=exact_keys(strict_json(PROV/"cross_role_overlap.json"),
        {"schema_version","blocking_collision_count","blocking_collisions","status"},code)
    if (cross["schema_version"]!="msae_independent_source_v6_cross_role_overlap_v1"
            or cross["blocking_collision_count"]!=len(cross["blocking_collisions"])
            or cross["blocking_collision_count"]!=0 or cross["blocking_collisions"]!=[] or cross["status"]!="eligible"):
        raise GateFailure(code)

    overlap=exact_keys(strict_json(PROV/"history_overlap.json"),
        {"schema_version","baseline_inventory_sha256","history_entries_sha256","history_unit_count",
         "history_adapter_census","candidate_utterance_count","blocking_collision_count","blocking_collisions",
         "quarantine_content_reads","opaque_binary_history_count","status"},code)
    if (overlap["schema_version"]!="msae_independent_source_v6_history_overlap_v1"
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
            if (not isinstance(classes,dict) or any(not isinstance(key,str) or not _is_count(value) or value<20 for key,value in classes.items())
                    or record["retained_class_count"]!=len(classes) or record["eligible"] is not (len(classes)>=2)):
                raise GateFailure(code)
            if record["eligible"]:eligible.add(task)
        eligible_sets.append(eligible)
    intersection=set.intersection(*eligible_sets)
    if (support["schema_version"]!="msae_independent_source_v6_support_v1" or support["floor_distinct_utterances"]!=20
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
    source={"schema_version":"msae_independent_source_v6_source_manifest_v1","source_commit":COMMIT,
            "partitions":source_counts,"source_text_published":False}
    if strict_json(PROV/"source_manifest.json")!=source:raise GateFailure(code)
    if strict_json(PROV/"license.json")!=_license():raise GateFailure(code)
    raw_hashes={sha_file(RAW/name) for name in [*SOURCE_FILES.values(),"README.md","LICENSE.txt"]}
    if strict_json(PROV/"source_family.json")!=_source_family(baseline,raw_hashes):raise GateFailure(code)
    if strict_json(PROV/"candidate_pedigree.json")!=candidate_pedigree():raise GateFailure(code)
    roles,dedup=deduplicate_roles(roles)
    if strict_json(PROV/"dedup.json")!=dedup:raise GateFailure(code)
    rows=_source_rows(roles);cross=_role_overlap(rows)
    cross_value={"schema_version":"msae_independent_source_v6_cross_role_overlap_v1",
                 "blocking_collision_count":len(cross),"blocking_collisions":cross,
                 "status":"eligible" if not cross else "ineligible"}
    if strict_json(PROV/"cross_role_overlap.json")!=cross_value:raise GateFailure(code)
    hits,unit_count,adapter_census=_history_overlap(rows,baseline)
    baseline["entries_sha256"]=sha_bytes(canonical_bytes(baseline["entries"]))
    if strict_json(PROV/"history_manifest.json")!=baseline:raise GateFailure(code)
    overlap={"schema_version":"msae_independent_source_v6_history_overlap_v1",
        "baseline_inventory_sha256":sha_file(PROV/"baseline_inventory.json"),
        "history_entries_sha256":baseline["entries_sha256"],"history_unit_count":unit_count,
        "history_adapter_census":adapter_census,"candidate_utterance_count":sum(map(len,rows.values())),
        "blocking_collision_count":len(hits),"blocking_collisions":hits,"quarantine_content_reads":0,
        "opaque_binary_history_count":baseline["counts"].get("binary_unscanned",0),
        "status":"eligible" if not hits else "ineligible"}
    if strict_json(PROV/"history_overlap.json")!=overlap:raise GateFailure(code)
    support=_support(rows);support["unsupported_tasks"]=["neutral_prefix_offset","entity_binary","entity_type","source_genre"]
    if strict_json(PROV/"support.json")!=support:raise GateFailure(code)
    role_manifest={"schema_version":"msae_independent_source_v6_role_manifest_v1","source_commit":COMMIT,"roles":{}}
    for role,upstream in (("discovery","train"),("calibration","dev")):
        values=rows[role]
        role_manifest["roles"][role]={"upstream_partition":upstream,"record_count":len(values),
            "entries":[{"zero_based_rank":i,"sent_id":item["sent_id"],
                        "source_record_sha256":_source_record_hash(item["sentence"])} for i,item in enumerate(values)]}
    if strict_json(PROV/"role_manifest.json")!=role_manifest:raise GateFailure(code)
    test_rows=assign_split([{"sent_id":sentence.sent_id,"normalized":normalized_sentence(sentence),"sentence":sentence}
                            for sentence in roles["test"]])
    split={"schema_version":"msae_independent_source_v6_split_manifest_v1","source_commit":COMMIT,
        "upstream_partition":"test","split_algorithm":"sha256-canonical-json-array-v1-even-C1-odd-C2",
        "record_count":len(test_rows),"C1_count":sum(item["panel"]=="C1" for item in test_rows),
        "C2_count":sum(item["panel"]=="C2" for item in test_rows),
        "entries":[{"sent_id":item["sent_id"],"panel":item["panel"],"zero_based_rank":item["zero_based_rank"],
                    "split_key_sha256":item["split_key_sha256"],
                    "source_record_sha256":_source_record_hash(item["sentence"])} for item in test_rows]}
    if strict_json(PROV/"split_manifest.json")!=split:raise GateFailure(code)
    payload_bytes=b"".join(canonical_file_bytes({"schema_version":"msae_independent_source_v6_payload_v1",
        "source_repo":REPO,"source_commit":COMMIT,"upstream_partition":"test","panel":item["panel"],
        "split_key_sha256":item["split_key_sha256"],"sent_id":item["sent_id"],
        "tokens":_token_objects(item["sentence"])}) for item in test_rows)
    return {"sha256":sha_bytes(payload_bytes),"size":len(payload_bytes),"record_count":len(test_rows)}


def verify_terminal() -> None:
    seal_path=PROV/"seal.json";rejection_path=PROV/"rejection.json"
    if present_path(seal_path)==present_path(rejection_path):
        raise GateFailure("terminal_state_cardinality")
    if present_path(rejection_path):
        rejection=strict_json(rejection_path)
        exact_keys(rejection,{"schema_version","status","failure_code","scientific_artifact_inventory",
            "payload_state","payload_created","payload","source_content_reported",
            "model_operations_initiated_by_builder","gpu_queries_initiated_by_builder",
            "training_runs_initiated_by_builder","terminal_process_snapshot","training_root_status",
            "model_scoring_authorized","k2_or_branch_training_authorized","stage_c_authorized",
            "next_action"},"rejection_verification")
        verify_process_snapshot_schema(rejection["terminal_process_snapshot"],"rejection_verification")
        current_payload_state=payload_state();final_state=current_payload_state[0]
        payload_created=(final_state.get("type")=="regular" and final_state.get("mode")==0o600
                         and final_state.get("nlink")==1 and "sha256" in final_state)
        expected_payload=({key:final_state[key] for key in ("path","sha256","size","mode","nlink")}
                          if payload_created else None)
        if (rejection.get("schema_version")!="msae_independent_source_v6_rejection_v1"
                or rejection.get("status")!="rejected" or not isinstance(rejection.get("failure_code"),str)
                or not rejection.get("failure_code") or rejection.get("source_content_reported") is not False
                or rejection.get("model_operations_initiated_by_builder")!=0
                or rejection.get("gpu_queries_initiated_by_builder")!=0
                or rejection.get("training_runs_initiated_by_builder")!=0
                or rejection.get("model_scoring_authorized") is not False
                or rejection.get("k2_or_branch_training_authorized") is not False
                or rejection.get("stage_c_authorized") is not False
                or rejection.get("training_root_status") not in {"unchanged","changed","unavailable"}
                or rejection.get("next_action")!="new_reviewed_protocol_only"
                or rejection.get("payload_created") is not payload_created
                or rejection.get("payload")!=expected_payload):
            raise GateFailure("rejection_verification")
        if rejection.get("scientific_artifact_inventory")!=scientific_artifact_inventory():
            raise GateFailure("rejection_artifact_inventory_drift")
        if rejection.get("payload_state")!=current_payload_state:
            raise GateFailure("rejection_payload_state_drift")
        if rejection.get("payload_created"):
            item=rejection.get("payload") or {};payload=ROOT/item.get("path","");st=payload.lstat()
            if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode)!=0o600 or st.st_nlink!=1
                    or st.st_size!=item.get("size") or sha_file(payload)!=item.get("sha256")):
                raise GateFailure("rejected_payload_verification")
        return
    seal=strict_json(seal_path)
    exact_keys(seal,{"schema_version","status","source_status","plan_sha256","plan_review_sha256",
        "program_sha256","acquisition_runner_sha256","test_sha256","artifact_sha256","payload",
        "model_operations_initiated_by_builder","gpu_queries_initiated_by_builder",
        "training_runs_initiated_by_builder","external_observation_scope","unsupported_tasks",
        "opaque_binary_history_excluded","document_speaker_cluster_inference_authorized"},"seal_verification")
    if (seal.get("schema_version")!="msae_independent_source_v6_seal_v1"
            or seal.get("status")!="independent_source_ready_for_future_prescore_protocol"
            or seal.get("source_status")!="previously_considered_but_project_source_use_unseen"
            or seal.get("plan_sha256")!=sha_file(ROOT/"docs/plan-msae-independent-source-v6.md")
            or seal.get("plan_review_sha256")!=sha_file(ROOT/"reports/adversarial/msae_independent_source_v6_plan_review.md")
            or seal.get("program_sha256")!=sha_file(Path(__file__))
            or seal.get("acquisition_runner_sha256")!=sha_file(ROOT/"scripts/acquire_msae_independent_source_v6.py")
            or seal.get("test_sha256")!=sha_file(ROOT/"tests/test_prepare_msae_independent_source_v6.py")
            or seal.get("model_operations_initiated_by_builder")!=0
            or seal.get("gpu_queries_initiated_by_builder")!=0
            or seal.get("training_runs_initiated_by_builder")!=0
            or seal.get("external_observation_scope")!="baseline_and_terminal_proc_snapshots_plus_training_root_diff"
            or seal.get("unsupported_tasks")!=["neutral_prefix_offset","entity_binary","entity_type","source_genre"]
            or seal.get("opaque_binary_history_excluded") is not True
            or seal.get("document_speaker_cluster_inference_authorized") is not False):
        raise GateFailure("seal_verification")
    _verify_predecessor_and_raw()
    expected_artifacts={
        "baseline_inventory.json","source_acquisition_entry.json","source_acquisition.json","source_family.json","candidate_pedigree.json","license.json",
        "document_group_census.json","source_manifest.json","dedup.json","history_manifest.json","history_overlap.json",
        "cross_role_overlap.json","support.json","role_manifest.json","split_manifest.json","post_process_snapshot.json",
        "preacquisition_alias_screen.json","historical_source_registry.json","preacquisition_authority_manifest.json"}
    bindings=seal.get("artifact_sha256",{})
    if set(bindings)!=expected_artifacts or any(sha_file(PROV/name)!=digest for name,digest in bindings.items()):
        raise GateFailure("seal_artifact_binding")
    expected_schemas={
        "baseline_inventory.json":"msae_independent_source_v6_baseline_inventory_v1",
        "source_acquisition_entry.json":"msae_independent_source_v6_source_acquisition_entry_v1",
        "source_acquisition.json":"msae_independent_source_v6_source_acquisition_v1",
        "source_family.json":"msae_independent_source_v6_source_family_v1",
        "candidate_pedigree.json":"msae_independent_source_v6_candidate_pedigree_v1",
        "license.json":"msae_independent_source_v6_license_v1",
        "document_group_census.json":"msae_independent_source_v6_document_group_census_v1",
        "source_manifest.json":"msae_independent_source_v6_source_manifest_v1",
        "dedup.json":"msae_independent_source_v6_dedup_v1",
        "history_manifest.json":"msae_independent_source_v6_baseline_inventory_v1",
        "history_overlap.json":"msae_independent_source_v6_history_overlap_v1",
        "cross_role_overlap.json":"msae_independent_source_v6_cross_role_overlap_v1",
        "support.json":"msae_independent_source_v6_support_v1",
        "role_manifest.json":"msae_independent_source_v6_role_manifest_v1",
        "split_manifest.json":"msae_independent_source_v6_split_manifest_v1",
        "post_process_snapshot.json":"msae_independent_source_v6_process_snapshot_v1",
        "preacquisition_alias_screen.json":"msae_independent_source_v5_preacquisition_alias_screen_v2",
        "historical_source_registry.json":"msae_independent_source_v5_historical_source_registry_v1",
        "preacquisition_authority_manifest.json":"msae_independent_source_v6_preacquisition_authority_v1",
    }
    for name,schema in expected_schemas.items():
        if strict_json(PROV/name).get("schema_version")!=schema:raise GateFailure("artifact_schema_verification")
    validate_scientific_artifacts()
    reconstructed_payload=reconstruct_scientific_artifacts()
    split=strict_json(PROV/"split_manifest.json");entries=split.get("entries",[])
    exact_keys(split,{"schema_version","source_commit","upstream_partition","split_algorithm","record_count",
                      "C1_count","C2_count","entries"},"split_manifest_verification")
    ranks=[item.get("zero_based_rank") for item in entries]
    if (any(not isinstance(item,dict) or set(item)!={"sent_id","panel","zero_based_rank","split_key_sha256","source_record_sha256"}
            for item in entries)
            or split.get("schema_version")!="msae_independent_source_v6_split_manifest_v1"
            or split.get("source_commit")!=COMMIT
            or split.get("split_algorithm")!="sha256-canonical-json-array-v1-even-C1-odd-C2"
            or split.get("record_count")!=len(entries)
            or split.get("C1_count")!=sum(item.get("panel")=="C1" for item in entries)
            or split.get("C2_count")!=sum(item.get("panel")=="C2" for item in entries)
            or split.get("upstream_partition")!="test"
            or ranks!=list(range(len(entries)))
            or any(item.get("panel")!=("C1" if item.get("zero_based_rank",-1)%2==0 else "C2") for item in entries)
            or any(not re.fullmatch(r"[0-9a-f]{64}",str(item.get("split_key_sha256",""))) for item in entries)
            or any(not re.fullmatch(r"[0-9a-f]{64}",str(item.get("source_record_sha256",""))) for item in entries)):
        raise GateFailure("split_manifest_verification")
    roles=strict_json(PROV/"role_manifest.json")
    exact_keys(roles,{"schema_version","source_commit","roles"},"role_manifest_verification")
    role_values=roles.get("roles",{})
    if (roles.get("schema_version")!="msae_independent_source_v6_role_manifest_v1"
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
                     "k2_or_branch_training_authorized","stage_c_authorized","seal_sha256"},"no_training_gate_verification")
    if (gate.get("schema_version")!="msae_independent_source_v6_no_training_gate_v1"
            or gate.get("status")!="pending_terminal_seal"
            or gate.get("terminal_status_if_seal_matches")!=seal.get("status")
            or gate.get("seal_sha256")!=sha_file(seal_path) or gate.get("model_scoring_authorized") is not False
            or gate.get("k2_or_branch_training_authorized") is not False or gate.get("stage_c_authorized") is not False):
        raise GateFailure("no_training_gate_verification")


def main() -> None:
    p=argparse.ArgumentParser();p.add_argument("command",choices=("baseline","authority","prepare","verify"));a=p.parse_args()
    if a.command=="baseline":build_baseline()
    elif a.command=="authority":build_authority_manifest()
    elif a.command=="prepare":
        try:build_ready()
        except (GateFailure,OSError,UnicodeError,ValueError,KeyError,TypeError,json.JSONDecodeError) as error:
            code=str(error) if isinstance(error,GateFailure) else "boundary_"+type(error).__name__
            retain_rejection(code);raise
    else:
        verify_terminal()

if __name__ == "__main__":
    main()
