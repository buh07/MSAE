from pathlib import Path
import os,subprocess

ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/'scripts/launch_sae_selection_bridge_v2_tmux.sh').read_text()

def test_launcher_uses_distinct_sessions_and_one_shot_namespaces():
 assert 'trained_copy_sae_basis_selection_v1_20260814' in TEXT
 assert 'causal_manifold_bridge_v2_technical_20260814' in TEXT
 assert 'two free GPUs unavailable' in TEXT

def test_launcher_records_uuid_pid_and_waits_only_to_first_access():
 assert 'nvidia-smi --query-compute-apps=gpu_uuid,pid' in TEXT
 assert '010_FIT_ACCESS_MAY_HAVE_OCCURRED.json' in TEXT
 assert 'write_manifest' in TEXT and 'token_sha256' in TEXT

def test_launcher_cleans_partial_launch_and_stale_lock():
 assert 'cleanup_all_workers' in TEXT
 assert '.stale.$$' in TEXT
 assert 'bridge partial launch failed' in TEXT

def test_launcher_lock_lifecycle_self_test_executes(tmp_path):
 env=dict(os.environ,MSAE_ROOT=str(tmp_path),MSAE_LAUNCHER_SELF_TEST='1')
 got=subprocess.run(['bash',str(ROOT/'scripts/launch_sae_selection_bridge_v2_tmux.sh')],env=env,text=True,capture_output=True,check=True)
 assert 'LAUNCHER_SELF_TEST_PASS' in got.stdout
