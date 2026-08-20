import os,signal,subprocess,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/"scripts/launch_trained_control_next_studies_v1_r2_tmux.sh").read_text()

def test_launcher_records_manifest_handoff_and_pid_uuid_proof():
    for token in ("write_manifest","GPU_LOCK_OWNERSHIP_TRANSFERRED","FIT_ACCESS_MAY_HAVE_OCCURRED","query-compute-apps=gpu_uuid,pid","worker_token"):
        assert token in TEXT

def test_launcher_has_stale_owner_and_partial_failure_cleanup():
    assert 'kill -0 "$pid"' in TEXT
    assert 'tmux kill-session -t "$s"' in TEXT
    assert 'cleanup_all_workers' in TEXT

def test_one_gpu_failure_cleans_reserved_global_lock(tmp_path):
    fake=tmp_path/"bin";fake.mkdir();root=tmp_path/"root";(root/"reports/provenance").mkdir(parents=True)
    (fake/"tmux").write_text('#!/bin/sh\n[ "$1" = has-session ] && exit 1\nexit 0\n')
    (fake/"nvidia-smi").write_text('#!/bin/sh\ncase "$*" in *query-gpu*) echo "0, GPU-MSAE-LAUNCH-TEST, 0, 0";; esac\n')
    for p in fake.iterdir():p.chmod(0o755)
    lock=Path('/tmp/msae_gpu_GPU-MSAE-LAUNCH-TEST.lockdir')
    if lock.exists():subprocess.run(['rm','-rf',str(lock)],check=True)
    lock.mkdir();(lock/'owner').write_text('coordinator:99999999\n')
    env={**os.environ,"PATH":f"{fake}:{os.environ['PATH']}","MSAE_ROOT":str(root)}
    proc=subprocess.run(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,capture_output=True,text=True)
    assert proc.returncode!=0 and not lock.exists() and 'two free GPUs unavailable' in proc.stderr

def _mock_runtime(tmp_path,mode):
    tmp_path.mkdir(parents=True);fake=tmp_path/'bin';fake.mkdir();root=tmp_path/'root';(root/'reports/provenance').mkdir(parents=True);state=tmp_path/'state';state.mkdir()
    tmux='''#!/bin/bash
set -u
state="$MOCK_STATE";mode="$MOCK_MODE";cmd="$1";shift
session=""
for ((i=1;i<=$#;i++)); do [[ "${!i}" == -s || "${!i}" == -t ]] && { j=$((i+1));session="${!j}";session="${session%%:*}"; }; done
case "$cmd" in
 has-session) [[ -f "$state/$session.pid" ]] && kill -0 "$(cat "$state/$session.pid")" 2>/dev/null;;
 new-session)
  count=0;[[ -f "$state/count" ]] && count=$(cat "$state/count");count=$((count+1));echo "$count" >"$state/count"
  [[ "$mode" == partial && "$count" == 2 ]] && exit 1
  sleep 300 >/dev/null 2>&1 & pid=$!;echo "$pid" >"$state/$session.pid"
  [[ "$mode" == crash ]] && kill "$pid"
  if [[ "$count" == 2 && ( "$mode" == success || "$mode" == pid_remap ) ]]; then
   for spec in "trained_copy_sae_capacity_v1_r2_run_20260813:$state/trained_copy_sae_capacity_v1_r2_20260813.pid" "causal_manifold_bridge_v1_r2_run_20260813:$state/causal_manifold_bridge_v1_r2_20260813.pid"; do
    dir="${spec%%:*}";pf="${spec#*:}";mkdir -p "$MSAE_ROOT/reports/provenance/$dir/events";p=$(cat "$pf");printf '{"pid":%s}\n' "$p" >"$MSAE_ROOT/reports/provenance/$dir/events/000_RUN_START_NO_PANEL_ACCESS.json";echo '{}' >"$MSAE_ROOT/reports/provenance/$dir/events/010_FIT_ACCESS_MAY_HAVE_OCCURRED.json"
   done
  fi;;
 display-message) [[ "$mode" == display_fail ]] && exit 41;[[ "$mode" == signal_pre_handoff ]] && sleep 30;cat "$state/$session.pid";;
 kill-session) [[ -f "$state/$session.pid" ]] && { kill "$(cat "$state/$session.pid")" 2>/dev/null || true;rm -f "$state/$session.pid"; };;
 *) exit 0;;
esac
'''
    smi='''#!/bin/bash
case "$*" in
 *query-gpu*) printf '0, GPU-MSAE-MOCK-A, 0, 0\n1, GPU-MSAE-MOCK-B, 0, 0\n';;
 *query-compute-apps*)
  if [[ ( "$MOCK_MODE" == success || "$MOCK_MODE" == pid_remap ) && -f "$MOCK_STATE/trained_copy_sae_capacity_v1_r2_20260813.pid" && -f "$MOCK_STATE/causal_manifold_bridge_v1_r2_20260813.pid" ]]; then
   a=$(cat "$MOCK_STATE/trained_copy_sae_capacity_v1_r2_20260813.pid");b=$(cat "$MOCK_STATE/causal_manifold_bridge_v1_r2_20260813.pid")
   [[ "$MOCK_MODE" == success ]] && printf 'GPU-MSAE-MOCK-A, %s\nGPU-MSAE-MOCK-B, %s\n' "$a" "$b" || printf 'GPU-MSAE-MOCK-A, %s\nGPU-MSAE-MOCK-B, %s\n' "$b" "$a"
  fi;;
 *) echo '0, 0';;
esac
'''
    (fake/'tmux').write_text(tmux);(fake/'nvidia-smi').write_text(smi)
    (fake/'python').write_text('''#!/bin/bash
if [[ "$MOCK_MODE" == token_fail && "$#" -eq 1 && "$1" == - ]]; then exit 42;fi
if [[ "$MOCK_MODE" == manifest_fail && "${2:-}" == *LAUNCH.json ]]; then exit 42;fi
exec "$REAL_PYTHON" "$@"
''')
    (fake/'mkdir').write_text('''#!/bin/bash
if [[ "$MOCK_MODE" == metadata_fail && "$#" -eq 1 && "$1" == /tmp/msae_gpu_GPU-MSAE-MOCK-A.lockdir ]]; then
  : >"$1"
  exit 0
fi
if [[ "$MOCK_MODE" == stale_race && "$#" -eq 1 && "$1" == /tmp/msae_gpu_GPU-MSAE-MOCK-A.lockdir ]]; then
  count=0
  [[ -f "$MOCK_STATE/stale_race_mkdir_count" ]] && count=$(cat "$MOCK_STATE/stale_race_mkdir_count")
  count=$((count+1));printf '%s\n' "$count" >"$MOCK_STATE/stale_race_mkdir_count"
  if [[ "$count" -eq 2 ]]; then
    /usr/bin/mkdir "$1" || exit 1
    printf 'replacement-token\n' >"$1/token"
    printf 'coordinator:%s\n' "$REPLACEMENT_PID" >"$1/owner"
    exit 1
  fi
fi
exec /usr/bin/mkdir "$@"
''')
    for p in fake.iterdir():p.chmod(0o755)
    env={**os.environ,'PATH':f"{fake}:{os.environ['PATH']}",'MSAE_ROOT':str(root),'MOCK_STATE':str(state),'MOCK_MODE':mode,'REAL_PYTHON':os.path.realpath(__import__('sys').executable),'MSAE_HANDSHAKE_ITERATIONS':'2','MSAE_HANDSHAKE_SLEEP':'0.01'}
    return root,state,env

def _clear_mock_locks():
    for uuid in ('GPU-MSAE-MOCK-A','GPU-MSAE-MOCK-B'):
        subprocess.run(['rm','-rf',f'/tmp/msae_gpu_{uuid}.lockdir'],check=True)

def test_partial_launch_and_crash_timeout_cleanup(tmp_path):
    for mode in ('partial','crash','timeout','display_fail','manifest_fail'):
        _clear_mock_locks();root,state,env=_mock_runtime(tmp_path/mode,mode)
        proc=subprocess.run(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,capture_output=True,text=True)
        assert proc.returncode!=0
        assert all(not Path(f'/tmp/msae_gpu_GPU-MSAE-MOCK-{x}.lockdir').exists() for x in ('A','B'))

def test_token_generation_failure_cannot_leave_ownerless_lock(tmp_path):
    _clear_mock_locks();root,state,env=_mock_runtime(tmp_path/'token_fail','token_fail')
    proc=subprocess.run(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,capture_output=True,text=True)
    assert proc.returncode!=0
    assert all(not Path(f'/tmp/msae_gpu_GPU-MSAE-MOCK-{x}.lockdir').exists() for x in ('A','B'))

def test_lock_metadata_failure_removes_partially_acquired_path(tmp_path):
    _clear_mock_locks();root,state,env=_mock_runtime(tmp_path/'metadata_fail','metadata_fail')
    proc=subprocess.run(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,capture_output=True,text=True)
    assert proc.returncode!=0
    assert all(not Path(f'/tmp/msae_gpu_GPU-MSAE-MOCK-{x}.lockdir').exists() for x in ('A','B'))

def test_stale_reacquisition_race_preserves_live_replacement_owner(tmp_path):
    _clear_mock_locks();root,state,env=_mock_runtime(tmp_path/'stale_race','stale_race');env['REPLACEMENT_PID']=str(os.getpid())
    replacement=Path('/tmp/msae_gpu_GPU-MSAE-MOCK-A.lockdir');replacement.mkdir();(replacement/'owner').write_text('coordinator:99999999\n')
    proc=subprocess.run(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,capture_output=True,text=True)
    assert proc.returncode!=0 and 'two free GPUs unavailable' in proc.stderr
    assert replacement.is_dir()
    assert (replacement/'token').read_text().strip()=='replacement-token'
    assert (replacement/'owner').read_text().strip()==f'coordinator:{os.getpid()}'
    subprocess.run(['rm','-rf',str(replacement)],check=True)
    assert not Path('/tmp/msae_gpu_GPU-MSAE-MOCK-B.lockdir').exists()

def test_success_and_pid_remap_proof(tmp_path):
    _clear_mock_locks();root,state,env=_mock_runtime(tmp_path/'success','success');proc=subprocess.run(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,capture_output=True,text=True)
    assert proc.returncode==0 and 'SESSION=trained_copy_sae_capacity_v1_r2_20260813' in proc.stdout
    for pf in state.glob('*.pid'):
        subprocess.run(['kill',pf.read_text().strip()],check=False)
    _clear_mock_locks()
    root,state,env=_mock_runtime(tmp_path/'remap','pid_remap');proc=subprocess.run(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,capture_output=True,text=True)
    assert proc.returncode!=0 and all(not Path(f'/tmp/msae_gpu_GPU-MSAE-MOCK-{x}.lockdir').exists() for x in ('A','B'))

def test_signal_after_handoff_cleans_workers_and_locks(tmp_path):
    _clear_mock_locks();root,state,env=_mock_runtime(tmp_path/'signal','timeout');env['MSAE_HANDSHAKE_ITERATIONS']='1000';env['MSAE_HANDSHAKE_SLEEP']='0.05'
    proc=subprocess.Popen(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    locks=[Path(f'/tmp/msae_gpu_GPU-MSAE-MOCK-{x}.lockdir') for x in ('A','B')]
    for _ in range(100):
        if all((p/'HANDOFF').exists() for p in locks):break
        time.sleep(.02)
    assert all((p/'HANDOFF').exists() for p in locks);proc.terminate();proc.communicate(timeout=5)
    assert proc.returncode!=0 and all(not p.exists() for p in locks)

def test_signal_before_handoff_kills_started_workers(tmp_path):
    _clear_mock_locks();root,state,env=_mock_runtime(tmp_path/'pre_signal','signal_pre_handoff');proc=subprocess.Popen(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    for _ in range(100):
        if len(list(state.glob('*.pid')))>=1:break
        time.sleep(.02)
    assert len(list(state.glob('*.pid')))>=1;os.killpg(proc.pid,signal.SIGTERM);proc.communicate(timeout=15)
    assert proc.returncode!=0
    for pf in state.glob('*.pid'):assert subprocess.run(['kill','-0',pf.read_text().strip()],capture_output=True).returncode!=0
    _clear_mock_locks()

def test_cleanup_does_not_delete_replacement_owner_lock(tmp_path):
    _clear_mock_locks();root,state,env=_mock_runtime(tmp_path/'replacement','timeout');env['MSAE_HANDSHAKE_ITERATIONS']='1000';env['MSAE_HANDSHAKE_SLEEP']='0.05';proc=subprocess.Popen(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    lock=Path('/tmp/msae_gpu_GPU-MSAE-MOCK-A.lockdir')
    for _ in range(100):
        if (lock/'HANDOFF').exists():break
        time.sleep(.02)
    assert (lock/'HANDOFF').exists();subprocess.run(['rm','-rf',str(lock)],check=True);lock.mkdir();(lock/'token').write_text('replacement-token\n');(lock/'owner').write_text('coordinator:777777\n');proc.terminate();proc.communicate(timeout=5)
    assert lock.exists() and (lock/'token').read_text().strip()=='replacement-token';subprocess.run(['rm','-rf',str(lock)],check=True);subprocess.run(['rm','-rf','/tmp/msae_gpu_GPU-MSAE-MOCK-B.lockdir'],check=True)

def test_launcher_requires_two_distinct_atomic_locks():
    assert 'mkdir "$d"' in TEXT and '((${#IDX[@]}==2))' in TEXT

def test_namespace_collision_fails_before_gpu_reservation(tmp_path):
    fake=tmp_path/'bin';fake.mkdir();root=tmp_path/'root';(root/'reports/provenance').mkdir(parents=True);(root/'results/trained_copy_sae_capacity_v1_r2_20260813').mkdir(parents=True)
    marker=tmp_path/'nvidia_called';(fake/'nvidia-smi').write_text(f'#!/bin/sh\ntouch "{marker}"\nexit 1\n');(fake/'tmux').write_text('#!/bin/sh\nexit 1\n')
    for p in fake.iterdir():p.chmod(0o755)
    env={**os.environ,'PATH':f"{fake}:{os.environ['PATH']}",'MSAE_ROOT':str(root)};proc=subprocess.run(['bash',str(ROOT/'scripts/launch_trained_control_next_studies_v1_r2_tmux.sh')],env=env,capture_output=True,text=True)
    assert proc.returncode!=0 and 'recovery namespace exists' in proc.stderr and not marker.exists()
