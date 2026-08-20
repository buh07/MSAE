#!/usr/bin/env python3
"""Run one v2 stage under a UUID-specific, child-inherited GPU lease."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
from typing import Any


LOCK_ROOT = Path("/tmp/msae_atlas_gpu_locks")


def atomic_json(path: Path, value: Any, *, create_once: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{os.getpid()}.tmp"
    payload = json.dumps(value, sort_keys=True, indent=2) + "\n"
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(payload); handle.flush(); os.fsync(handle.fileno())
    if create_once:
        try:
            os.link(temporary, path)
        except FileExistsError:
            temporary.unlink()
            raise RuntimeError(f"create-once path exists: {path}")
        temporary.unlink()
    else:
        os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(directory_fd)
    finally: os.close(directory_fd)


def process_start_ticks(pid: int) -> int:
    fields = Path(f"/proc/{pid}/stat").read_text().split()
    return int(fields[21])


def secure_lock_fd(uuid: str) -> tuple[int, Path]:
    old_umask = os.umask(0o077)
    try:
        try: LOCK_ROOT.mkdir(mode=0o700)
        except FileExistsError: pass
        info = LOCK_ROOT.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(f"unsafe GPU lock root: {LOCK_ROOT}")
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise RuntimeError(f"GPU lock root ownership/mode mismatch: {LOCK_ROOT}")
        lock_path = LOCK_ROOT / f"{uuid}.lock"
        try:
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            entry = lock_path.lstat()
            if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
                raise RuntimeError(f"unsafe GPU lock path: {lock_path}")
            if entry.st_uid != os.getuid() or stat.S_IMODE(entry.st_mode) != 0o600:
                raise RuntimeError(f"GPU lock ownership/mode mismatch: {lock_path}")
            fd = os.open(lock_path, os.O_RDWR | os.O_NOFOLLOW)
        entry = os.fstat(fd)
        if not stat.S_ISREG(entry.st_mode) or entry.st_uid != os.getuid() or stat.S_IMODE(entry.st_mode) != 0o600:
            os.close(fd); raise RuntimeError("opened GPU lock changed identity")
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd); raise RuntimeError(f"GPU lease already held: {uuid}")
        os.dup2(fd, 200, inheritable=True)
        if fd != 200: os.close(fd)
        os.set_inheritable(200, True)
        return 200, lock_path
    finally:
        os.umask(old_umask)


def gpu_state(uuid: str) -> tuple[int, int]:
    output = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,uuid,memory.used", "--format=csv,noheader,nounits"], text=True,
    )
    matches=[]
    for line in output.splitlines():
        idx, found, memory = [item.strip() for item in line.split(",")]
        if found == uuid: matches.append((int(idx), int(memory)))
    if len(matches) != 1: raise RuntimeError(f"configured GPU UUID is absent/ambiguous: {uuid}")
    return matches[0]


def command_sha(command: list[str]) -> str:
    return hashlib.sha256(b"\0".join(os.fsencode(item) for item in command)).hexdigest()


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-root",type=Path,required=True);parser.add_argument("--job",required=True)
    parser.add_argument("--uuid",required=True);parser.add_argument("--log",type=Path,required=True)
    parser.add_argument("command",nargs=argparse.REMAINDER)
    args=parser.parse_args(); command=list(args.command)
    if command and command[0] == "--": command=command[1:]
    if not command: parser.error("command required after --")
    args.log.parent.mkdir(parents=True,exist_ok=True)
    leases=args.run_root/"leases"; jobs=args.run_root/"jobs"; leases.mkdir(parents=True,exist_ok=True);jobs.mkdir(parents=True,exist_ok=True)
    lease_fd,lock_path=secure_lock_fd(args.uuid)
    gpu_index,memory=gpu_state(args.uuid)
    if memory >= 1024:
        os.close(lease_fd);raise RuntimeError(f"GPU {args.uuid} is not idle: {memory} MiB")
    config_sha=os.environ["MSAE_V2_CONFIG_SHA256"]
    wrapper_pid=os.getpid();wrapper_ticks=process_start_ticks(wrapper_pid);cmd_sha=command_sha(command)
    env=os.environ.copy();env.update({"CUDA_VISIBLE_DEVICES":args.uuid,"MSAE_EXPECTED_GPU_UUID":args.uuid,
        "MSAE_V2_PRODUCER_JOB":args.job,"MSAE_V2_PRODUCER_COMMAND_SHA256":cmd_sha,
        "PYTHONHASHSEED":"20260802","HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1","HF_DATASETS_OFFLINE":"1"})
    child:subprocess.Popen[bytes]|None=None;stopping=False
    def stop_child(signum: int, _frame: object) -> None:
        nonlocal stopping
        if stopping:return
        stopping=True
        if child is not None and child.poll() is None:
            try: os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:return
            deadline=time.monotonic()+60
            while child.poll() is None and time.monotonic()<deadline:time.sleep(0.2)
            if child.poll() is None:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
    signal.signal(signal.SIGTERM,stop_child);signal.signal(signal.SIGINT,stop_child)
    started=time.time();exit_code=125
    with args.log.open("ab",buffering=0) as log:
        header=f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}] job={args.job} uuid={args.uuid} command={command!r}\n"
        log.write(header.encode())
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,pass_fds=(200,))
        child_ticks=process_start_ticks(child.pid)
        lease_record={"schema_version":"atlas_measurement_v2_gpu_lease_v1","job":args.job,"host":os.uname().nodename,
            "gpu_uuid":args.uuid,"gpu_index":gpu_index,"lock_path":str(lock_path),"fd":200,
            "wrapper_pid":wrapper_pid,"wrapper_start_ticks":wrapper_ticks,"child_pid":child.pid,
            "child_start_ticks":child_ticks,"command":command,"command_sha256":cmd_sha,
            "config_sha256":config_sha,"started_unix":started}
        payload=(json.dumps(lease_record,sort_keys=True)+"\n").encode()
        os.lseek(lease_fd,0,os.SEEK_SET);os.ftruncate(lease_fd,0);os.write(lease_fd,payload);os.fsync(lease_fd)
        atomic_json(leases/f"{args.job}.json",lease_record,create_once=True)
        atomic_json(jobs/f"{args.job}.started.json",lease_record,create_once=True)
        exit_code=child.wait()
    terminal={"schema_version":"atlas_measurement_v2_job_terminal_v1","job":args.job,"exit_code":exit_code,
        "wrapper_pid":wrapper_pid,"wrapper_start_ticks":wrapper_ticks,"child_pid":child.pid if child else None,
        "command_sha256":cmd_sha,"config_sha256":config_sha,"ended_unix":time.time()}
    atomic_json(jobs/f"{args.job}.terminal.json",terminal,create_once=True)
    os.close(lease_fd)
    return exit_code


if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print(f"GPU runner failed: {exc}",file=sys.stderr,flush=True)
        raise
