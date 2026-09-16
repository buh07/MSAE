#!/usr/bin/env python3
"""Reviewed, one-shot upstream acquisition runner for MSAE v5."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"configs/msae_independent_source_v5/acquisition.json"
PROV=ROOT/"reports/provenance/msae_independent_source_v5"
AUTHORITY=PROV/"preacquisition_authority_manifest.json"
AUTHORITY_REVIEW=ROOT/"reports/adversarial/msae_independent_source_v5_preacquisition_authority_review.md"
ENTRY=PROV/"source_acquisition_entry.json"
REPORT=PROV/"source_acquisition.json"
REJECTION=PROV/"source_acquisition_rejection.json"
COMMIT="5552572ac2c5aac1538e43edb7f7a8d2224f12de"
REPO="https://github.com/UniversalDependencies/UD_English-ParTUT.git"
FILES=["en_partut-ud-train.conllu","en_partut-ud-dev.conllu","en_partut-ud-test.conllu","README.md","LICENSE.txt"]
RAW=ROOT/"data/msae_independent_source_v5/raw"/COMMIT
PRIVATE=ROOT/"data/msae_independent_source_v5/private"
BASELINE=PROV/"baseline_inventory.json"
GENERATED_PREFIXES=(".git/",".venv-atlas/",".pytest_cache/",".generated/")
V5_PREFIX="data/msae_independent_source_v5/"
FORBIDDEN_PROCESS_TOKENS=("torchrun","train_msae","msae_train","branch_training","run_branch_train",
                          "deepspeed","accelerate launch","nvidia-smi","cuda_visible_devices")

class AcquisitionFailure(RuntimeError): pass
COMMAND_RECORDS:list[dict[str,Any]]=[]
FAILURE_CONTEXT:dict[str,Any]={}
SCRATCH_CLEANUP_OK=True
SCRATCH_CREATED=False

def canonical(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()+b"\n"

def sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def is_hex(value:Any,length:int)->bool:
    return isinstance(value,str) and len(value)==length and all(ch in "0123456789abcdef" for ch in value)
def is_count(value:Any)->bool:return isinstance(value,int) and not isinstance(value,bool) and value>=0

def strict_json_bytes(payload:bytes)->Any:
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise AcquisitionFailure("duplicate_json_member")
            out[key]=value
        return out
    return json.loads(payload.decode("utf-8"),object_pairs_hook=pairs,
                      parse_constant=lambda _x:(_ for _ in ()).throw(AcquisitionFailure("nonfinite_json")))

def open_root_file(path:Path)->int:
    """Open a regular file while refusing symlinks in every repository component."""
    try:rel=path.relative_to(ROOT)
    except ValueError:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        if not stat.S_ISREG(os.fstat(fd).st_mode):os.close(fd);raise AcquisitionFailure("nonregular_open")
        return fd
    root_stat=ROOT.lstat()
    if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):raise AcquisitionFailure("unsafe_repository_root")
    dfd=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        opened_root=os.fstat(dfd)
        if (opened_root.st_dev,opened_root.st_ino)!=(root_stat.st_dev,root_stat.st_ino):
            raise AcquisitionFailure("repository_root_identity_drift")
        for component in rel.parent.parts:
            next_fd=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=dfd)
            os.close(dfd);dfd=next_fd
        fd=os.open(rel.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=dfd)
    finally:os.close(dfd)
    if not stat.S_ISREG(os.fstat(fd).st_mode):os.close(fd);raise AcquisitionFailure("nonregular_open")
    return fd

def read_bytes_nofollow(path:Path)->bytes:
    fd=open_root_file(path)
    try:
        before=os.fstat(fd);chunks=[]
        while True:
            block=os.read(fd,1024*1024)
            if not block:break
            chunks.append(block)
        after=os.fstat(fd)
        if (before.st_dev,before.st_ino,before.st_mode,before.st_size,before.st_mtime_ns)!=(
                after.st_dev,after.st_ino,after.st_mode,after.st_size,after.st_mtime_ns):
            raise AcquisitionFailure("file_mutated_while_reading")
        return b"".join(chunks)
    finally:os.close(fd)

def sha_file(path:Path)->str:return sha_bytes(read_bytes_nofollow(path))

def strict_json(path:Path)->Any:
    payload=read_bytes_nofollow(path);value=strict_json_bytes(payload)
    if payload!=canonical(value):raise AcquisitionFailure("noncanonical_public_json")
    return value

def exact_keys(value:Any,keys:set[str],code:str)->dict[str,Any]:
    if not isinstance(value,dict) or set(value)!=keys:raise AcquisitionFailure(code)
    return value

def hash_fd(fd:int)->str:
    os.lseek(fd,0,os.SEEK_SET);h=hashlib.sha256()
    while True:
        block=os.read(fd,1024*1024)
        if not block:break
        h.update(block)
    return h.hexdigest()

def git_blob_fd(fd:int,size:int)->str:
    os.lseek(fd,0,os.SEEK_SET);h=hashlib.sha1(usedforsecurity=False);h.update(f"blob {size}\0".encode())
    while True:
        block=os.read(fd,1024*1024)
        if not block:break
        h.update(block)
    return h.hexdigest()

def open_root_dir(path:Path)->int:
    try:rel=path.relative_to(ROOT)
    except ValueError:raise AcquisitionFailure("directory_outside_repository")
    root_stat=ROOT.lstat();dfd=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    if (os.fstat(dfd).st_dev,os.fstat(dfd).st_ino)!=(root_stat.st_dev,root_stat.st_ino):
        os.close(dfd);raise AcquisitionFailure("repository_root_identity_drift")
    try:
        for component in rel.parts:
            next_fd=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=dfd)
            os.close(dfd);dfd=next_fd
        return dfd
    except BaseException:
        os.close(dfd);raise

def present(path:Path)->bool:
    """Return path presence without following a final-component symlink."""
    try:path.lstat()
    except FileNotFoundError:return False
    return True

def regular_hash(path:Path)->str|None:
    try:st=path.lstat()
    except (FileNotFoundError,OSError):return None
    if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):return None
    try:return sha_file(path)
    except (OSError,AcquisitionFailure):return None

def expected_config()->dict[str,Any]:
    return {
        "schema_version":"msae_independent_source_v5_acquisition_v1",
        "source_repo":REPO,"source_commit":COMMIT,"files":FILES,
        "clone_argv":["git","-c","credential.helper=","-c","core.hooksPath=/dev/null","clone","--quiet","--filter=blob:none","--no-checkout",REPO,"${CLONE_DIR}"],
        "checkout_argv":["git","-c","credential.helper=","-c","core.hooksPath=/dev/null","-c","core.sparseCheckout=true","-C","${CLONE_DIR}","checkout","--quiet","--detach",COMMIT],
        "environment":{"GIT_CONFIG_NOSYSTEM":"1","GIT_TERMINAL_PROMPT":"0","HOME":"${EMPTY_HOME}","PATH":"/usr/bin:/bin"},
        "variables_required_absent":["ALL_PROXY","HTTPS_PROXY","HTTP_PROXY","NO_PROXY","all_proxy","https_proxy","http_proxy","no_proxy"],
        "required_runtime_input":"authority_review_sha256","review_argument_flag":"--authority-review-sha256",
        "head_argv":["git","-C","${CLONE_DIR}","rev-parse","HEAD"],
        "tree_argv":["git","-C","${CLONE_DIR}","rev-parse","${SOURCE_COMMIT}^{tree}"],
        "ls_tree_argv":["git","-C","${CLONE_DIR}","ls-tree","-z","${SOURCE_COMMIT}","--",*FILES],
        "hash_object_argv":["git","-C","${CLONE_DIR}","hash-object","--no-filters","${CHECKED_OUT_FILE}"],
        "ignore_argv":["git","check-ignore","-v","${IGNORED_SENTINEL}"],
        "sparse_checkout_paths":FILES,
        "stdout_policy":"quiet_hash_only_no_source_content","stderr_policy":"quiet_hash_only_no_source_content",
    }

def validate_config(value:Any)->dict[str,Any]:
    if value!=expected_config():raise AcquisitionFailure("acquisition_config_drift")
    return value

def cleanup_created_temp(dfd:int,name:str,identity:tuple[int,int])->None:
    current=os.stat(name,dir_fd=dfd,follow_symlinks=False)
    if (current.st_dev,current.st_ino)!=identity:raise AcquisitionFailure("temporary_identity_changed")
    os.unlink(name,dir_fd=dfd);os.fsync(dfd)

def atomic_json(path:Path,value:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True);data=canonical(value)
    try:path.relative_to(ROOT)
    except ValueError:dfd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    else:dfd=open_root_dir(path.parent)
    parent_stat=os.fstat(dfd);tmp="."+path.name+".building"
    try:
        for name in (tmp,path.name):
            try:os.stat(name,dir_fd=dfd,follow_symlinks=False)
            except FileNotFoundError:continue
            raise AcquisitionFailure("acquisition_report_path_exists")
        fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644,dir_fd=dfd)
        created=os.fstat(fd);identity=(created.st_dev,created.st_ino)
        try:
            os.fchmod(fd,0o644);position=0
            while position<len(data):
                written=os.write(fd,data[position:])
                if written<=0:raise OSError("short write")
                position+=written
            os.fsync(fd)
        except BaseException:
            os.close(fd);cleanup_created_temp(dfd,tmp,identity);raise
        else:os.close(fd)
        try:os.link(tmp,path.name,src_dir_fd=dfd,dst_dir_fd=dfd,follow_symlinks=False)
        except BaseException:
            cleanup_created_temp(dfd,tmp,identity);raise
        cleanup_created_temp(dfd,tmp,identity);final=os.stat(path.name,dir_fd=dfd,follow_symlinks=False)
        if not stat.S_ISREG(final.st_mode) or stat.S_IMODE(final.st_mode)!=0o644 or final.st_nlink!=1:
            raise AcquisitionFailure("acquisition_report_install")
        os.fsync(dfd)
    finally:os.close(dfd)

def run(name:str,argv:list[str],env:dict[str,str],cwd:Path)->tuple[bytes,bytes]:
    result=subprocess.run(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    COMMAND_RECORDS.append({"name":name,"argv":argv,"exit_status":result.returncode,
                            "stdout_bytes":len(result.stdout),"stdout_sha256":sha_bytes(result.stdout),
                            "stderr_bytes":len(result.stderr),"stderr_sha256":sha_bytes(result.stderr)})
    if result.returncode!=0:raise AcquisitionFailure("command_failed")
    return result.stdout,result.stderr

def expand(values:list[str],clone_dir:str,home:str,checked_out_file:str="")->list[str]:
    return [item.replace("${CLONE_DIR}",clone_dir).replace("${EMPTY_HOME}",home)
            .replace("${SOURCE_COMMIT}",COMMIT).replace("${CHECKED_OUT_FILE}",checked_out_file) for item in values]

def require_clean_target()->None:
    protected=(ENTRY,ENTRY.with_name("."+ENTRY.name+".building"),REPORT,REJECTION,
               REPORT.with_name("."+REPORT.name+".building"),
               REJECTION.with_name("."+REJECTION.name+".building"),RAW.parent.parent)
    if any(present(path) for path in protected):
        raise AcquisitionFailure("acquisition_target_preexists")
    data=ROOT/"data"
    if present(data):
        data_stat=data.lstat()
        if not stat.S_ISDIR(data_stat.st_mode) or stat.S_ISLNK(data_stat.st_mode):
            raise AcquisitionFailure("unsafe_data_root")

def valid_public_final(path:Path)->dict[str,Any]:
    fd=open_root_file(path)
    try:
        before=os.fstat(fd);chunks=[]
        while True:
            block=os.read(fd,1024*1024)
            if not block:break
            chunks.append(block)
        after=os.fstat(fd)
    finally:os.close(fd)
    if ((before.st_dev,before.st_ino,before.st_mode,before.st_size,before.st_mtime_ns)!=(
            after.st_dev,after.st_ino,after.st_mode,after.st_size,after.st_mtime_ns)
            or stat.S_IMODE(after.st_mode)!=0o644 or after.st_nlink!=1):
        raise AcquisitionFailure("invalid_preacquisition_state")
    payload=b"".join(chunks);value=strict_json_bytes(payload)
    if payload!=canonical(value):raise AcquisitionFailure("invalid_preacquisition_state")
    return value

def validate_entry(value:dict[str,Any],manifest_sha:str,review_sha:str,baseline_sha:str)->None:
    exact_keys(value,{"schema_version","status","authority_manifest_sha256","authority_review_sha256",
                      "baseline_inventory_sha256","config_sha256","runner_sha256","source_repo",
                      "source_commit","files","subprocesses_started","model_scoring_authorized",
                      "k2_or_branch_training_authorized","stage_c_authorized"},"invalid_preacquisition_state")
    if (value.get("schema_version")!="msae_independent_source_v5_source_acquisition_entry_v1"
            or value.get("status")!="entered" or value.get("authority_manifest_sha256")!=manifest_sha
            or value.get("authority_review_sha256")!=review_sha or value.get("baseline_inventory_sha256")!=baseline_sha
            or value.get("config_sha256")!=sha_file(CONFIG) or value.get("runner_sha256")!=sha_file(Path(__file__))
            or value.get("source_repo")!=REPO or value.get("source_commit")!=COMMIT or value.get("files")!=FILES
            or value.get("subprocesses_started")!=0 or value.get("model_scoring_authorized") is not False
            or value.get("k2_or_branch_training_authorized") is not False or value.get("stage_c_authorized") is not False):
        raise AcquisitionFailure("invalid_preacquisition_state")

COMMAND_KEYS={"name","argv","exit_status","stdout_bytes","stdout_sha256","stderr_bytes","stderr_sha256"}
SUCCESS_KEYS={
    "schema_version","source_repo","source_commit","resolved_head","tree_object_sha1",
    "tree_verified_from_ls_tree","tree_paths","tree_blob_sha1","files","authority_manifest_sha256",
    "authority_review_sha256","source_acquisition_entry_sha256","acquisition_gate_argument",
    "config_sha256","runner_sha256","executed_clone_argv","executed_checkout_argv","environment",
    "clone_dir","empty_home","proxy_variables_present","ignore_checks","commands",
    "sparse_checkout_sha256","raw_directory","command_exit_status","head_stdout_sha256",
    "head_stderr_sha256","tree_stdout_sha256","tree_stderr_sha256","ls_tree_stdout_sha256",
    "ls_tree_stderr_sha256","clone_stdout_sha256","clone_stderr_sha256","checkout_stdout_sha256",
    "checkout_stderr_sha256","source_content_printed","network_access","model_operations",
    "gpu_queries","training_runs",
}
REJECTION_KEYS={
    "schema_version","status","failure_code","bindings","raw_namespace_exists",
    "source_acquisition_entry_sha256","partial_raw_metadata","commands","sparse_checkout_sha256",
    "source_content_printed","terminal_process_snapshot","training_root_status",
    "model_operations_initiated_by_runner","gpu_queries_initiated_by_runner",
    "training_runs_initiated_by_runner","model_scoring_authorized",
    "k2_or_branch_training_authorized","stage_c_authorized","next_action",
}
FILE_KEYS={"sha256","size","git_blob_sha1","mode","nlink"}

def validate_command_records(commands:Any,expected_names:list[str],config:dict[str,Any],
                             clone_dir:str,empty_home:str,*,allow_last_failure:bool=False)->None:
    if not isinstance(commands,list) or [item.get("name") if isinstance(item,dict) else None for item in commands]!=expected_names:
        raise AcquisitionFailure("invalid_preacquisition_state")
    expected_argv=[
        [*expand(config["ignore_argv"],clone_dir,empty_home)[:-1],"data/msae_independent_source_v5/raw/sentinel"],
        [*expand(config["ignore_argv"],clone_dir,empty_home)[:-1],"data/msae_independent_source_v5/private/sentinel"],
        expand(config["clone_argv"],clone_dir,empty_home),
        expand(config["checkout_argv"],clone_dir,empty_home),
        expand(config["head_argv"],clone_dir,empty_home),
        expand(config["tree_argv"],clone_dir,empty_home),
        expand(config["ls_tree_argv"],clone_dir,empty_home),
        *[expand(config["hash_object_argv"],clone_dir,empty_home,name) for name in FILES],
    ]
    for index,item in enumerate(commands):
        exact_keys(item,COMMAND_KEYS,"invalid_preacquisition_state")
        exit_ok=item["exit_status"]==0 or (allow_last_failure and index==len(commands)-1 and item["exit_status"]!=0)
        if (not exit_ok or item["argv"]!=expected_argv[index] or not is_count(item["stdout_bytes"])
                or not is_count(item["stderr_bytes"]) or not is_hex(item["stdout_sha256"],64)
                or not is_hex(item["stderr_sha256"],64) or not isinstance(item["exit_status"],int)
                or isinstance(item["exit_status"],bool)):
            raise AcquisitionFailure("invalid_preacquisition_state")

def validate_process_snapshot(value:Any)->None:
    exact_keys(value,{"schema_version","observation_scope","forbidden_tokens","process_count","entries",
                      "forbidden_identity_count","status"},"invalid_preacquisition_state")
    if not isinstance(value["entries"],list) or any(not isinstance(item,dict) for item in value["entries"]):
        raise AcquisitionFailure("invalid_preacquisition_state")
    if (value["schema_version"]!="msae_independent_source_v5_process_snapshot_v1"
            or value["observation_scope"]!="point_in_time_proc_snapshot"
            or value["forbidden_tokens"]!=list(FORBIDDEN_PROCESS_TOKENS)
            or value["process_count"]!=len(value["entries"])
            or value["forbidden_identity_count"]!=sum(bool(item.get("forbidden_codes")) for item in value["entries"])
            or value["status"] != ("eligible" if value["forbidden_identity_count"]==0 else "ineligible")
            or not is_count(value["process_count"]) or not is_count(value["forbidden_identity_count"])
            or any(not isinstance(item,dict)
                   or set(item)!={"pid","start_ticks","executable_basename","command_sha256","forbidden_codes"}
                   or not is_count(item["pid"]) or not isinstance(item["start_ticks"],str)
                   or not isinstance(item["executable_basename"],str) or not is_hex(item["command_sha256"],64)
                   or not isinstance(item["forbidden_codes"],list)
                   or item["forbidden_codes"]!=sorted(set(item["forbidden_codes"]))
                   or any(code not in FORBIDDEN_PROCESS_TOKENS for code in item["forbidden_codes"])
                   for item in value["entries"])):
        raise AcquisitionFailure("invalid_preacquisition_state")

def validate_existing_raw(report:dict[str,Any])->None:
    fds=[]
    try:
        v5fd=open_root_dir(RAW.parent.parent);fds.append(v5fd)
        rawrootfd=os.open("raw",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=v5fd);fds.append(rawrootfd)
        commitfd=os.open(COMMIT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=rawrootfd);fds.append(commitfd)
        for fd,mode in ((v5fd,0o700),(rawrootfd,0o700),(commitfd,0o555)):
            st=os.fstat(fd)
            if stat.S_IMODE(st.st_mode)!=mode:raise AcquisitionFailure("invalid_preacquisition_state")
        if sorted(os.listdir(v5fd))!=["raw"] or sorted(os.listdir(rawrootfd))!=[COMMIT] or sorted(os.listdir(commitfd))!=sorted(FILES):
            raise AcquisitionFailure("invalid_preacquisition_state")
        commit_stat=os.fstat(commitfd);raw_record=exact_keys(report.get("raw_directory"),
            {"device","inode","mode","nlink"},"invalid_preacquisition_state")
        if raw_record!={"device":commit_stat.st_dev,"inode":commit_stat.st_ino,
                       "mode":stat.S_IMODE(commit_stat.st_mode),"nlink":commit_stat.st_nlink}:
            raise AcquisitionFailure("invalid_preacquisition_state")
        exact_keys(report.get("files"),set(FILES),"invalid_preacquisition_state")
        for name in FILES:
            item=exact_keys(report["files"][name],FILE_KEYS,"invalid_preacquisition_state")
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=commitfd)
            try:st=os.fstat(fd);digest=hash_fd(fd);blob_digest=git_blob_fd(fd,st.st_size)
            finally:os.close(fd)
            if (not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode)!=0o444 or st.st_nlink!=1
                    or st.st_size!=item["size"] or digest!=item["sha256"] or item["mode"]!=0o444
                    or item["nlink"]!=1 or item["git_blob_sha1"]!=blob_digest
                    or report["tree_blob_sha1"][name]!=blob_digest):raise AcquisitionFailure("invalid_preacquisition_state")
    except (OSError,KeyError,TypeError) as error:
        raise AcquisitionFailure("invalid_preacquisition_state") from error
    finally:
        for fd in reversed(fds):os.close(fd)

def partial_raw_metadata()->list[dict[str,Any]]:
    partial=[];namespace=RAW.parent.parent
    if present(namespace):
        root_stat=namespace.lstat()
        if stat.S_ISDIR(root_stat.st_mode) and not stat.S_ISLNK(root_stat.st_mode):
            for base,dirs,files in os.walk(namespace,followlinks=False):
                root=Path(base)
                for name in sorted([*dirs,*files]):
                    path=root/name;st=path.lstat()
                    partial.append({"path":path.relative_to(ROOT).as_posix(),
                                    "type":"directory" if stat.S_ISDIR(st.st_mode) else "regular" if stat.S_ISREG(st.st_mode) else "special",
                                    "size":st.st_size,"mode":stat.S_IMODE(st.st_mode),"device":st.st_dev,
                                    "inode":st.st_ino,"nlink":st.st_nlink})
                dirs[:]=[name for name in dirs if stat.S_ISDIR((root/name).lstat().st_mode)
                         and not stat.S_ISLNK((root/name).lstat().st_mode)]
    return partial

def validate_success_report(report:dict[str,Any],entry_sha:str,manifest_sha:str,review_sha:str,
                            baseline_sha:str)->None:
    exact_keys(report,SUCCESS_KEYS,"invalid_preacquisition_state")
    config=validate_config(strict_json(CONFIG));clone_dir=report.get("clone_dir");empty_home=report.get("empty_home")
    if not isinstance(clone_dir,str) or not isinstance(empty_home,str):raise AcquisitionFailure("invalid_preacquisition_state")
    clone_path=Path(clone_dir);home_path=Path(empty_home)
    if (not clone_path.is_absolute() or clone_path.name!="repo" or home_path.name!="home"
            or clone_path.parent!=home_path.parent or not clone_path.parent.name.startswith("msae-v5-acquire-")):
        raise AcquisitionFailure("invalid_preacquisition_state")
    expected_clone=expand(config["clone_argv"],clone_dir,empty_home)
    expected_checkout=expand(config["checkout_argv"],clone_dir,empty_home)
    expected_environment={key:(empty_home if value=="${EMPTY_HOME}" else value) for key,value in config["environment"].items()}
    blobs=exact_keys(report.get("tree_blob_sha1"),set(FILES),"invalid_preacquisition_state")
    files=exact_keys(report.get("files"),set(FILES),"invalid_preacquisition_state")
    if (report["schema_version"]!="msae_independent_source_v5_source_acquisition_v1"
            or report["source_repo"]!=REPO or report["source_commit"]!=COMMIT or report["resolved_head"]!=COMMIT
            or not isinstance(report["tree_object_sha1"],str) or len(report["tree_object_sha1"])!=40
            or report["tree_verified_from_ls_tree"] is not True or report["tree_paths"]!=FILES
            or report["authority_manifest_sha256"]!=manifest_sha or report["authority_review_sha256"]!=review_sha
            or report["source_acquisition_entry_sha256"]!=entry_sha
            or report["acquisition_gate_argument"]!=review_sha or report["config_sha256"]!=sha_file(CONFIG)
            or report["runner_sha256"]!=sha_file(Path(__file__)) or report["executed_clone_argv"]!=expected_clone
            or report["executed_checkout_argv"]!=expected_checkout or report["environment"]!=expected_environment
            or report["proxy_variables_present"]!=[]
            or report["sparse_checkout_sha256"]!=sha_bytes(("\n".join("/"+name for name in FILES)+"\n").encode())
            or report["command_exit_status"]!={"ignore_raw":0,"ignore_private":0,"clone":0,"checkout":0,
                                                   "head":0,"tree":0,"ls_tree":0,"hash_object_count":len(FILES)}
            or report["source_content_printed"] is not False
            or report["network_access"]!="git_clone_and_checkout_only"
            or report["model_operations"]!=0 or report["gpu_queries"]!=0 or report["training_runs"]!=0):
        raise AcquisitionFailure("invalid_preacquisition_state")
    if not is_hex(report["tree_object_sha1"],40) or any(not is_hex(value,40) for value in blobs.values()):
        raise AcquisitionFailure("invalid_preacquisition_state")
    for name,item in files.items():
        exact_keys(item,FILE_KEYS,"invalid_preacquisition_state")
        if (not is_hex(item["sha256"],64) or item["git_blob_sha1"]!=blobs[name]
                or not is_count(item["size"]) or item["mode"]!=0o444 or item["nlink"]!=1):
            raise AcquisitionFailure("invalid_preacquisition_state")
    exact_keys(report["raw_directory"],{"device","inode","mode","nlink"},"invalid_preacquisition_state")
    if (report["raw_directory"]["mode"]!=0o555 or not is_count(report["raw_directory"]["nlink"])
            or report["raw_directory"]["nlink"]<2 or not is_count(report["raw_directory"]["device"])
            or not is_count(report["raw_directory"]["inode"])):
        raise AcquisitionFailure("invalid_preacquisition_state")
    expected_names=["ignore_raw","ignore_private","clone","checkout","head","tree","ls_tree",*[
        "hash_object:"+name for name in FILES]]
    validate_command_records(report["commands"],expected_names,config,clone_dir,empty_home)
    by_name={item["name"]:item for item in report["commands"]}
    ignores=report["ignore_checks"]
    if (not isinstance(ignores,list) or len(ignores)!=2):raise AcquisitionFailure("invalid_preacquisition_state")
    for index,(name,path) in enumerate((("ignore_raw","data/msae_independent_source_v5/raw/sentinel"),
                                        ("ignore_private","data/msae_independent_source_v5/private/sentinel"))):
        exact_keys(ignores[index],{"path","stdout_sha256","stderr_sha256","exit_status"},"invalid_preacquisition_state")
        if (ignores[index]!={"path":path,"stdout_sha256":by_name[name]["stdout_sha256"],
                            "stderr_sha256":by_name[name]["stderr_sha256"],"exit_status":0}):
            raise AcquisitionFailure("invalid_preacquisition_state")
    direct={
        "clone_stdout_sha256":by_name["clone"]["stdout_sha256"],"clone_stderr_sha256":by_name["clone"]["stderr_sha256"],
        "checkout_stdout_sha256":by_name["checkout"]["stdout_sha256"],"checkout_stderr_sha256":by_name["checkout"]["stderr_sha256"],
        "head_stdout_sha256":by_name["head"]["stdout_sha256"],"head_stderr_sha256":by_name["head"]["stderr_sha256"],
        "tree_stdout_sha256":by_name["tree"]["stdout_sha256"],"tree_stderr_sha256":by_name["tree"]["stderr_sha256"],
        "ls_tree_stdout_sha256":by_name["ls_tree"]["stdout_sha256"],"ls_tree_stderr_sha256":by_name["ls_tree"]["stderr_sha256"],
    }
    if any(report[key]!=value for key,value in direct.items()):raise AcquisitionFailure("invalid_preacquisition_state")
    if any(report[key]!=sha_bytes(b"") for key in ("clone_stdout_sha256","clone_stderr_sha256",
            "checkout_stdout_sha256","checkout_stderr_sha256","head_stderr_sha256","tree_stderr_sha256","ls_tree_stderr_sha256")):
        raise AcquisitionFailure("invalid_preacquisition_state")
    if report["head_stdout_sha256"]!=sha_bytes((COMMIT+"\n").encode()) or report["tree_stdout_sha256"]!=sha_bytes((report["tree_object_sha1"]+"\n").encode()):
        raise AcquisitionFailure("invalid_preacquisition_state")
    if (by_name["clone"]["stdout_bytes"]!=0 or by_name["clone"]["stderr_bytes"]!=0
            or by_name["checkout"]["stdout_bytes"]!=0 or by_name["checkout"]["stderr_bytes"]!=0
            or by_name["head"]["stdout_bytes"]!=41 or by_name["head"]["stderr_bytes"]!=0
            or by_name["tree"]["stdout_bytes"]!=41 or by_name["tree"]["stderr_bytes"]!=0
            or by_name["ls_tree"]["stderr_bytes"]!=0):raise AcquisitionFailure("invalid_preacquisition_state")
    expected_ls=b"".join(f"100644 blob {blobs[name]}\t{name}\0".encode() for name in sorted(FILES))
    if (by_name["ls_tree"]["stdout_bytes"]!=len(expected_ls)
            or by_name["ls_tree"]["stdout_sha256"]!=sha_bytes(expected_ls)):
        raise AcquisitionFailure("invalid_preacquisition_state")
    for name in FILES:
        item=by_name["hash_object:"+name];expected=(blobs[name]+"\n").encode()
        if (item["stdout_bytes"]!=len(expected) or item["stdout_sha256"]!=sha_bytes(expected)
                or item["stderr_bytes"]!=0 or item["stderr_sha256"]!=sha_bytes(b"")):
            raise AcquisitionFailure("invalid_preacquisition_state")
    validate_existing_raw(report)

def validate_rejection_report(rejection:dict[str,Any],entry_sha:str,manifest_sha:str,review_sha:str,
                              baseline_sha:str)->None:
    exact_keys(rejection,REJECTION_KEYS,"invalid_preacquisition_state")
    expected_bindings={"authority_manifest_sha256":manifest_sha,"authority_review_sha256":review_sha,
        "baseline_inventory_sha256":baseline_sha,"config_sha256":sha_file(CONFIG),
        "runner_sha256":sha_file(Path(__file__)),"supplied_authority_review_sha256":review_sha,
        "sparse_checkout_sha256":sha_bytes(("\n".join("/"+name for name in FILES)+"\n").encode()),
        "source_acquisition_entry_sha256":entry_sha}
    exact_keys(rejection["bindings"],set(expected_bindings),"invalid_preacquisition_state")
    validate_process_snapshot(rejection["terminal_process_snapshot"])
    metadata=rejection["partial_raw_metadata"]
    metadata_keys={"path","type","size","mode","device","inode","nlink"}
    if (not isinstance(metadata,list) or any(not isinstance(item,dict) or set(item)!=metadata_keys for item in metadata)
            or metadata!=partial_raw_metadata()):raise AcquisitionFailure("invalid_preacquisition_state")
    commands=rejection["commands"]
    all_names=["ignore_raw","ignore_private","clone","checkout","head","tree","ls_tree",*[
        "hash_object:"+name for name in FILES]]
    names=[item.get("name") if isinstance(item,dict) else None for item in commands]
    if names!=all_names[:len(names)] or len(names)>len(all_names):raise AcquisitionFailure("invalid_preacquisition_state")
    if commands:
        clone_dir="";empty_home=""
        # Rejection command records still bind exact immutable argv structure; dynamic scratch paths
        # are recovered from the clone command when it was reached, otherwise only ignore argv exists.
        clone_record=next((item for item in commands if item.get("name")=="clone"),None)
        if clone_record:
            clone_dir=clone_record["argv"][-1];empty_home=str(Path(clone_dir).parent/"home")
        else:
            clone_dir=str(Path("/tmp/msae-v5-acquire-placeholder/repo"));empty_home=str(Path(clone_dir).parent/"home")
        config=validate_config(strict_json(CONFIG))
        for item in commands:
            exact_keys(item,COMMAND_KEYS,"invalid_preacquisition_state")
            if (not isinstance(item["argv"],list) or not all(isinstance(x,str) for x in item["argv"])
                    or not isinstance(item["exit_status"],int) or isinstance(item["exit_status"],bool)
                    or not is_count(item["stdout_bytes"]) or not is_count(item["stderr_bytes"])
                    or not is_hex(item["stdout_sha256"],64) or not is_hex(item["stderr_sha256"],64)):
                raise AcquisitionFailure("invalid_preacquisition_state")
        nonzero=[index for index,item in enumerate(commands) if item["exit_status"]!=0]
        if nonzero not in ([],[len(commands)-1]):raise AcquisitionFailure("invalid_preacquisition_state")
        if nonzero and rejection["failure_code"]!="command_failed":raise AcquisitionFailure("invalid_preacquisition_state")
        if clone_record:
            validate_command_records(commands,names,config,clone_dir,empty_home,allow_last_failure=True)
        else:
            sentinels=("data/msae_independent_source_v5/raw/sentinel",
                       "data/msae_independent_source_v5/private/sentinel")
            for index,item in enumerate(commands):
                if item["argv"]!=[*config["ignore_argv"][:-1],sentinels[index]]:
                    raise AcquisitionFailure("invalid_preacquisition_state")
    if (rejection["schema_version"]!="msae_independent_source_v5_source_acquisition_rejection_v1"
            or rejection["status"]!="rejected" or not isinstance(rejection["failure_code"],str)
            or not rejection["failure_code"] or rejection["bindings"]!=expected_bindings
            or rejection["raw_namespace_exists"]!=present(RAW.parent.parent)
            or rejection["source_acquisition_entry_sha256"]!=entry_sha
            or rejection["sparse_checkout_sha256"]!=expected_bindings["sparse_checkout_sha256"]
            or rejection["source_content_printed"] is not False
            or rejection["training_root_status"] not in {"unchanged","changed","unavailable"}
            or rejection["model_operations_initiated_by_runner"]!=0
            or rejection["gpu_queries_initiated_by_runner"]!=0 or rejection["training_runs_initiated_by_runner"]!=0
            or rejection["model_scoring_authorized"] is not False
            or rejection["k2_or_branch_training_authorized"] is not False
            or rejection["stage_c_authorized"] is not False
            or rejection["next_action"]!="new_reviewed_protocol_only"):
        raise AcquisitionFailure("invalid_preacquisition_state")

def preflight_state(manifest_sha:str,review_sha:str,baseline_sha:str)->str:
    entry_temp=ENTRY.with_name("."+ENTRY.name+".building")
    report_temp=REPORT.with_name("."+REPORT.name+".building")
    rejection_temp=REJECTION.with_name("."+REJECTION.name+".building")
    if not any(present(path) for path in (ENTRY,entry_temp,REPORT,report_temp,REJECTION,rejection_temp,RAW.parent.parent)):
        require_clean_target();return "clean"
    if any(present(path) for path in (entry_temp,report_temp,rejection_temp)) or not present(ENTRY):
        raise AcquisitionFailure("invalid_preacquisition_state")
    entry=valid_public_final(ENTRY);validate_entry(entry,manifest_sha,review_sha,baseline_sha)
    if present(REPORT)==present(REJECTION):raise AcquisitionFailure("invalid_preacquisition_state")
    entry_sha=sha_file(ENTRY)
    if present(REPORT):
        report=valid_public_final(REPORT)
        validate_success_report(report,entry_sha,manifest_sha,review_sha,baseline_sha);return "success"
    rejection=valid_public_final(REJECTION)
    validate_rejection_report(rejection,entry_sha,manifest_sha,review_sha,baseline_sha)
    return "rejection"

def process_snapshot()->dict[str,Any]:
    forbidden=tuple(item.encode() for item in FORBIDDEN_PROCESS_TOKENS)
    entries=[];matches=[]
    for child in sorted(Path("/proc").iterdir(),key=lambda item:int(item.name) if item.name.isdigit() else -1):
        if not child.name.isdigit():continue
        try:
            raw=(child/"cmdline").read_bytes();stat_text=(child/"stat").read_text()
            stat_fields=stat_text[stat_text.rfind(")")+2:].split();exe=Path(os.readlink(child/"exe")).name
        except (FileNotFoundError,PermissionError,ProcessLookupError,OSError):continue
        codes=sorted(token.decode() for token in forbidden if token in raw.lower())
        item={"pid":int(child.name),"start_ticks":stat_fields[19],"executable_basename":exe,
              "command_sha256":sha_bytes(b"msae-v5/process\0"+raw),"forbidden_codes":codes}
        entries.append(item)
        if codes:matches.append(item)
    return {"schema_version":"msae_independent_source_v5_process_snapshot_v1",
            "observation_scope":"point_in_time_proc_snapshot","forbidden_tokens":[x.decode() for x in forbidden],
            "process_count":len(entries),"entries":entries,"forbidden_identity_count":len(matches),
            "status":"eligible" if not matches else "ineligible"}

def checkout_file_evidence(clone:Path,blobs:dict[str,str],config:dict[str,Any],environment:dict[str,str],
                           home:Path)->dict[str,dict[str,Any]]:
    clonefd=os.open(clone,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        result={}
        for name in FILES:
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=clonefd)
            try:
                st=os.fstat(fd);digest=hash_fd(fd)
            finally:os.close(fd)
            if not stat.S_ISREG(st.st_mode):raise AcquisitionFailure("checkout_file_type")
            hash_out,hash_err=run("hash_object:"+name,expand(config["hash_object_argv"],str(clone),str(home),name),environment,ROOT)
            if hash_err or hash_out.decode("ascii").strip()!=blobs[name]:raise AcquisitionFailure("blob_mismatch")
            result[name]={"sha256":digest,"size":st.st_size,"git_blob_sha1":blobs[name]}
        return result
    finally:os.close(clonefd)

def create_raw_namespace()->tuple[list[int],os.stat_result]:
    """Create and pin data/v5/raw/commit without path-following writes."""
    fds=[];rootfd=open_root_dir(ROOT);fds.append(rootfd)
    try:
        try:datafd=os.open("data",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=rootfd)
        except FileNotFoundError:
            os.mkdir("data",0o755,dir_fd=rootfd);os.fsync(rootfd)
            datafd=os.open("data",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=rootfd)
        fds.append(datafd)
        current=datafd
        for name,mode in (("msae_independent_source_v5",0o700),("raw",0o700),(COMMIT,0o700)):
            os.mkdir(name,mode,dir_fd=current);os.fsync(current)
            next_fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current)
            os.fchmod(next_fd,mode);os.fsync(next_fd);fds.append(next_fd);current=next_fd
        return fds,os.fstat(current)
    except BaseException:
        for fd in reversed(fds):os.close(fd)
        raise

def install_raw_files(clone:Path,file_evidence:dict[str,dict[str,Any]])->os.stat_result:
    fds,_created=create_raw_namespace();commitfd=fds[-1]
    clonefd=os.open(clone,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for name in FILES:
            sourcefd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=clonefd)
            targetfd=-1
            try:
                source_stat=os.fstat(sourcefd)
                if (not stat.S_ISREG(source_stat.st_mode) or source_stat.st_size!=file_evidence[name]["size"]
                        or hash_fd(sourcefd)!=file_evidence[name]["sha256"]):raise AcquisitionFailure("checkout_file_drift")
                os.lseek(sourcefd,0,os.SEEK_SET)
                targetfd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o444,dir_fd=commitfd)
                os.fchmod(targetfd,0o444)
                while True:
                    block=os.read(sourcefd,1024*1024)
                    if not block:break
                    position=0
                    while position<len(block):
                        written=os.write(targetfd,block[position:])
                        if written<=0:raise OSError("short raw write")
                        position+=written
                os.fsync(targetfd)
                target_stat=os.fstat(targetfd);target_digest=hash_fd(targetfd)
                if (target_digest!=file_evidence[name]["sha256"] or target_stat.st_size!=source_stat.st_size
                        or stat.S_IMODE(target_stat.st_mode)!=0o444 or target_stat.st_nlink!=1):
                    raise AcquisitionFailure("installed_file_drift")
                file_evidence[name].update(mode=0o444,nlink=1)
            finally:
                if targetfd>=0:os.close(targetfd)
                os.close(sourcefd)
        if sorted(os.listdir(commitfd))!=sorted(FILES):raise AcquisitionFailure("installed_file_set_drift")
        os.fchmod(commitfd,0o555);os.fsync(commitfd)
        for fd in reversed(fds[:-1]):os.fsync(fd)
        return os.fstat(commitfd)
    finally:
        os.close(clonefd)
        for fd in reversed(fds):os.close(fd)

def walk_history_paths():
    for base,dirs,files in os.walk(ROOT,followlinks=False):
        root=Path(base);relbase=root.relative_to(ROOT).as_posix();prefix="" if relbase=="." else relbase+"/"
        retained=[]
        for name in sorted(dirs):
            rel=prefix+name;st=(root/name).lstat()
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):raise AcquisitionFailure("training_root_special_path")
            if name=="__pycache__" or any((rel+"/").startswith(item) for item in GENERATED_PREFIXES) or rel.startswith(V5_PREFIX.rstrip("/")):
                continue
            retained.append(name)
        dirs[:]=retained
        for name in sorted(files):
            path=root/name;rel=path.relative_to(ROOT).as_posix()
            if not rel.startswith(".git/"):yield path,rel

def training_root_status()->str:
    try:
        baseline=strict_json(BASELINE);expected=baseline["training_root_entries"];current=[]
        by_path={item["path"]:item for item in expected}
        for path,rel in walk_history_paths():
            folded=rel.casefold();name=Path(folded).name
            if not (folded.startswith("results/") or "checkpoint" in folded or name=="train_metrics.jsonl"
                    or (folded.startswith("pilot_runs/") and Path(folded).suffix in {".pt",".pth",".ckpt",".safetensors"})):
                continue
            st=path.lstat()
            if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):return "changed"
            current.append({"path":rel,"size":st.st_size,"mode":stat.S_IMODE(st.st_mode),"inode":st.st_ino,
                            "mtime_ns":st.st_mtime_ns,"sha256":sha_file(path),
                            "disposition":by_path.get(rel,{}).get("disposition","new")})
        return "unchanged" if current==expected else "changed"
    except (AcquisitionFailure,OSError,UnicodeError,ValueError,KeyError,TypeError,json.JSONDecodeError):
        return "unavailable"

def main()->None:
    global SCRATCH_CREATED,SCRATCH_CLEANUP_OK
    COMMAND_RECORDS.clear();FAILURE_CONTEXT.clear();SCRATCH_CREATED=False;SCRATCH_CLEANUP_OK=True
    parser=argparse.ArgumentParser();parser.add_argument("--authority-review-sha256",required=True);args=parser.parse_args()
    config=strict_json(CONFIG);authority=strict_json(AUTHORITY);review=read_bytes_nofollow(AUTHORITY_REVIEW).decode("utf-8")
    manifest_sha=sha_file(AUTHORITY);baseline_sha=sha_file(BASELINE);review_sha=sha_file(AUTHORITY_REVIEW)
    FAILURE_CONTEXT.update(authority_manifest_sha256=manifest_sha,authority_review_sha256=review_sha,
                           baseline_inventory_sha256=baseline_sha,
                           config_sha256=sha_file(CONFIG),runner_sha256=sha_file(Path(__file__)),
                           supplied_authority_review_sha256=args.authority_review_sha256)
    if (len(args.authority_review_sha256)!=64 or args.authority_review_sha256!=review_sha
            or not review.startswith("VERDICT: SHIP") or manifest_sha not in review or baseline_sha not in review
            or authority.get("status")!="approved_for_exact_source_acquisition"
            or authority.get("artifact_sha256",{}).get("scripts/acquire_msae_independent_source_v5.py")!=sha_file(Path(__file__))
            or authority.get("artifact_sha256",{}).get("configs/msae_independent_source_v5/acquisition.json")!=sha_file(CONFIG)):
        raise AcquisitionFailure("authority_gate")
    config=validate_config(config)
    sparse_bytes=("\n".join("/"+name for name in FILES)+"\n").encode("utf-8")
    FAILURE_CONTEXT["sparse_checkout_sha256"]=sha_bytes(sparse_bytes)
    state=preflight_state(manifest_sha,review_sha,baseline_sha)
    if state in {"success","rejection"}:return
    entry={"schema_version":"msae_independent_source_v5_source_acquisition_entry_v1","status":"entered",
           "authority_manifest_sha256":manifest_sha,"authority_review_sha256":review_sha,
           "baseline_inventory_sha256":baseline_sha,"config_sha256":sha_file(CONFIG),
           "runner_sha256":sha_file(Path(__file__)),"source_repo":REPO,"source_commit":COMMIT,"files":FILES,
           "subprocesses_started":0,"model_scoring_authorized":False,
           "k2_or_branch_training_authorized":False,"stage_c_authorized":False}
    atomic_json(ENTRY,entry);entry_sha=sha_file(ENTRY)
    FAILURE_CONTEXT["source_acquisition_entry_sha256"]=entry_sha
    scratch=Path(tempfile.mkdtemp(prefix="msae-v5-acquire-",dir="/tmp"));SCRATCH_CREATED=True;SCRATCH_CLEANUP_OK=False
    clone=scratch/"repo";home=scratch/"home";report=None
    try:
        home.mkdir(mode=0o700)
        environment={key:(str(home) if value=="${EMPTY_HOME}" else value) for key,value in config["environment"].items()}
        if any(name in environment for name in config["variables_required_absent"]):raise AcquisitionFailure("proxy_environment")
        evidence={}
        ignore_outputs=[]
        for sentinel in ("data/msae_independent_source_v5/raw/sentinel","data/msae_independent_source_v5/private/sentinel"):
            out,err=run("ignore_raw" if "raw" in sentinel else "ignore_private",expand(config["ignore_argv"],str(clone),str(home)).copy()[:-1]+[sentinel],environment,ROOT)
            ignore_outputs.append({"path":sentinel,"stdout_sha256":sha_bytes(out),"stderr_sha256":sha_bytes(err),"exit_status":0})
        clone_argv=expand(config["clone_argv"],str(clone),str(home));out,err=run("clone",clone_argv,environment,ROOT)
        if out or err:raise AcquisitionFailure("nonquiet_clone")
        sparse=clone/".git/info/sparse-checkout";sparse.write_bytes(sparse_bytes)
        evidence.update(clone_stdout_sha256=sha_bytes(out),clone_stderr_sha256=sha_bytes(err))
        checkout_argv=expand(config["checkout_argv"],str(clone),str(home));out,err=run("checkout",checkout_argv,environment,ROOT)
        if out or err:raise AcquisitionFailure("nonquiet_checkout")
        evidence.update(checkout_stdout_sha256=sha_bytes(out),checkout_stderr_sha256=sha_bytes(err))
        head_out,head_err=run("head",expand(config["head_argv"],str(clone),str(home)),environment,ROOT)
        head=head_out.decode("ascii").strip()
        if head!=COMMIT or head_err:raise AcquisitionFailure("revision_drift")
        tree_out,tree_err=run("tree",expand(config["tree_argv"],str(clone),str(home)),environment,ROOT)
        tree=tree_out.decode("ascii").strip()
        if len(tree)!=40 or tree_err:raise AcquisitionFailure("tree_resolution")
        ls_out,ls_err=run("ls_tree",expand(config["ls_tree_argv"],str(clone),str(home)),environment,ROOT)
        if ls_err:raise AcquisitionFailure("ls_tree_stderr")
        blobs={}
        for record in ls_out.split(b"\0"):
            if not record:continue
            meta,name=record.split(b"\t",1);mode,kind,blob=meta.decode("ascii").split()
            decoded=name.decode("utf-8")
            if mode!="100644" or kind!="blob" or decoded not in FILES:raise AcquisitionFailure("tree_entry")
            blobs[decoded]=blob
        if set(blobs)!=set(FILES):raise AcquisitionFailure("tree_file_set")
        file_evidence=checkout_file_evidence(clone,blobs,config,environment,home)
        raw_stat=install_raw_files(clone,file_evidence)
        report={"schema_version":"msae_independent_source_v5_source_acquisition_v1","source_repo":REPO,"source_commit":COMMIT,
                "resolved_head":head,"tree_object_sha1":tree,"tree_verified_from_ls_tree":True,"tree_paths":FILES,
                "tree_blob_sha1":dict(sorted(blobs.items())),"files":dict(sorted(file_evidence.items())),
                "authority_manifest_sha256":manifest_sha,"authority_review_sha256":review_sha,
                "source_acquisition_entry_sha256":entry_sha,
                "acquisition_gate_argument":args.authority_review_sha256,"config_sha256":sha_file(CONFIG),
                "runner_sha256":sha_file(Path(__file__)),
                "executed_clone_argv":clone_argv,"executed_checkout_argv":checkout_argv,"environment":environment,
                "clone_dir":str(clone),"empty_home":str(home),"proxy_variables_present":[],"ignore_checks":ignore_outputs,
                "commands":COMMAND_RECORDS,"sparse_checkout_sha256":sha_bytes(sparse_bytes),
                "raw_directory":{"device":raw_stat.st_dev,"inode":raw_stat.st_ino,"mode":stat.S_IMODE(raw_stat.st_mode),"nlink":raw_stat.st_nlink},
                "command_exit_status":{"ignore_raw":0,"ignore_private":0,"clone":0,"checkout":0,"head":0,"tree":0,"ls_tree":0,"hash_object_count":len(FILES)},
                "head_stdout_sha256":sha_bytes(head_out),"head_stderr_sha256":sha_bytes(head_err),
                "tree_stdout_sha256":sha_bytes(tree_out),"tree_stderr_sha256":sha_bytes(tree_err),
                "ls_tree_stdout_sha256":sha_bytes(ls_out),"ls_tree_stderr_sha256":sha_bytes(ls_err),
                **evidence,"source_content_printed":False,"network_access":"git_clone_and_checkout_only","model_operations":0,"gpu_queries":0,"training_runs":0}
    finally:
        cleanup_error=None
        try:shutil.rmtree(scratch)
        except BaseException as error:cleanup_error=error
        try:scratch.lstat()
        except FileNotFoundError:SCRATCH_CLEANUP_OK=True
        else:SCRATCH_CLEANUP_OK=False
        if not SCRATCH_CLEANUP_OK:raise AcquisitionFailure("scratch_cleanup_failed") from cleanup_error
    if report is None:raise AcquisitionFailure("missing_success_report")
    validate_success_report(report,entry_sha,manifest_sha,review_sha,baseline_sha)
    atomic_json(REPORT,report)

def retain_failure(code:str)->None:
    if ("source_acquisition_entry_sha256" not in FAILURE_CONTEXT or not present(ENTRY)
            or any(present(path) for path in (REPORT,REJECTION,
                REPORT.with_name("."+REPORT.name+".building"),
                REJECTION.with_name("."+REJECTION.name+".building")))
            or (SCRATCH_CREATED and not SCRATCH_CLEANUP_OK)):return
    namespace=RAW.parent.parent
    partial=partial_raw_metadata()
    terminal=process_snapshot();training=training_root_status()
    value={"schema_version":"msae_independent_source_v5_source_acquisition_rejection_v1","status":"rejected",
           "failure_code":code,"bindings":FAILURE_CONTEXT,"raw_namespace_exists":present(namespace),
           "source_acquisition_entry_sha256":sha_file(ENTRY),
           "partial_raw_metadata":partial,"commands":COMMAND_RECORDS,
           "sparse_checkout_sha256":FAILURE_CONTEXT.get("sparse_checkout_sha256"),"source_content_printed":False,
           "terminal_process_snapshot":terminal,"training_root_status":training,
           "model_operations_initiated_by_runner":0,"gpu_queries_initiated_by_runner":0,"training_runs_initiated_by_runner":0,
           "model_scoring_authorized":False,"k2_or_branch_training_authorized":False,"stage_c_authorized":False,
           "next_action":"new_reviewed_protocol_only"}
    validate_rejection_report(value,value["source_acquisition_entry_sha256"],
        FAILURE_CONTEXT["authority_manifest_sha256"],FAILURE_CONTEXT["authority_review_sha256"],
        FAILURE_CONTEXT["baseline_inventory_sha256"])
    atomic_json(REJECTION,value)

def entrypoint()->None:
    try:main()
    except (AcquisitionFailure,OSError,UnicodeError,ValueError,KeyError,TypeError,json.JSONDecodeError) as error:
        for name,path in (("config_sha256",CONFIG),("runner_sha256",Path(__file__)),
                          ("authority_manifest_sha256",AUTHORITY),("authority_review_sha256",AUTHORITY_REVIEW),
                          ("baseline_inventory_sha256",BASELINE)):
            digest=regular_hash(path)
            if digest is not None:FAILURE_CONTEXT.setdefault(name,digest)
        retain_failure(str(error) if isinstance(error,AcquisitionFailure) else "boundary_"+type(error).__name__)
        raise

if __name__=="__main__":entrypoint()
