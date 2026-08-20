from __future__ import annotations
import base64, hashlib, inspect, json, sys
from functools import lru_cache
from pathlib import Path
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import atlas_rope_v6 as core
import run_atlas_rope_v6 as runner

@lru_cache(maxsize=1)
def selection():
    return runner._select_caps()

def test_attempt9_remains_signed_terminal_and_downstream_absent():
    payload=runner._verify_attempt9_terminal()
    assert payload['status']=='TERMINAL_GUM_VALIDATION_FAILED'
    assert payload['no_retry_authorized'] is True
    assert runner._attempt9_required_absences()==[]
    amendment=runner._verify_amendment_contract()
    assert core.sha256_file(runner.ATTEMPT9_TERMINAL)==amendment['attempt9_terminal']['sha256']

def test_exact_budget_aligned_calibration_union_selects_frozen_pair():
    chosen=selection()
    assert chosen['caps']==runner.SELECTED_CAPS
    assert chosen['coordinatewise_minima']==[[2e-5,5e-11]]
    assert chosen['passing_pairs']==[[2e-5,5e-11],[2e-5,1e-10]]
    assert chosen['selected_union_score']['cells']==60
    assert chosen['selected_union_score']['EWT']['status']=='PASS'
    assert chosen['selected_union_score']['GUM']['status']=='PASS'

def test_attempt9_gum_fails_old_caps_but_passes_amendment():
    ref,cand,rows,lineage=runner._verify_gum_history()
    assert lineage['attempt9_score_under_frozen_caps']['status']=='FAIL'
    assert lineage['exact_cached_replay']['status']=='PASS'
    assert lineage['signed_payload']['schema_version']=='atlas_rope_v5_attempt9_technical_bundle_v1'
    amended=core.score_grid(ref,cand,rows,atol=2e-5,relative_l2_cap=2e-5,cosine_cap=5e-11)
    assert amended['status']=='PASS' and len(amended['cells'])==30

def test_attempt7_is_separate_strict_evidence():
    result=runner._attempt7_family_scores(runner.SELECTED_CAPS)
    assert result['rows']==72
    assert all(v['status']=='PASS' for v in result['families'].values())
    assert 'selected_union_score' not in result

def test_signed_gum_sentinel_replays_without_gum_pass():
    assert not (runner.ATTEMPT9_ROOT/'validation/GUM_PASS.json').exists()
    result=runner._verify_gum_sentinel_history(runner.SELECTED_CAPS)
    assert result['status']=='PASS' and len(result['pairs'])==16

def test_only_gentle_technical_forward_is_reachable():
    source=inspect.getsource(runner)
    assert '_forward_units(model, references' in source
    assert '_forward_units(model, candidates' in source
    assert 'run_gum' not in source
    assert 'GENTLE_ONLY_VALIDATION_ONCE' in source
    amendment=json.loads(runner.AMENDMENT_CONFIG.read_text())
    assert amendment['new_ewt_or_gum_forward_authorized'] is False

def test_cap_search_order_is_frozen():
    assert runner.RELATIVE_SEARCH==(2e-6,5e-6,1e-5,2e-5)
    assert runner.COSINE_SEARCH==(1e-11,5e-11,1e-10)
    evaluated=selection()['evaluations']
    assert [(x['relative_l2'],x['cosine_distance']) for x in evaluated]==[(r,c) for r in runner.RELATIVE_SEARCH for c in runner.COSINE_SEARCH]

def test_write_signed_is_no_clobber(tmp_path,monkeypatch):
    private=Ed25519PrivateKey.generate(); key=tmp_path/'key.pem'
    key.write_bytes(private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    monkeypatch.setattr(core,'SIGNING_PUBLIC_KEY_BASE64',base64.b64encode(public).decode())
    monkeypatch.setattr(core,'SIGNING_KEY_FINGERPRINT',hashlib.sha256(public).hexdigest())
    monkeypatch.setattr(core,'RUN_ROOT',tmp_path/'run')
    out=tmp_path/'signed.json'; core.write_signed(out,{'x':1},key)
    with pytest.raises(RuntimeError,match='create-once'): core.write_signed(out,{'x':2},key)
    assert core.verify_envelope(core.read_json(out))=={'x':1}

def test_pipeline_shell_has_fail_closed_stage_terminalization():
    text=(ROOT/'scripts/run_atlas_rope_v6_pipeline.sh').read_text()
    assert 'trap terminalize ERR' in text
    assert 'TERMINAL_PIPELINE_STAGE_FAILED' in text
    assert text.index('run-gentle') < text.index('authorize-science') < text.index('extract-ewt') < text.index('extract-gum') < text.index('analyze')

def test_launcher_never_relaunches_terminal_or_completion():
    text=(ROOT/'scripts/launch_atlas_rope_v6_tmux.sh').read_text()
    assert 'signed terminal/completion already exists; not relaunching' in text
    assert 'tmux has-session' in text and 'tmux new-session -d' in text
    assert 'one-shot session already produced a signed terminal' in text
    assert 'one-shot session already produced a signed completion' in text
    assert 'unexpected early tmux exit' in text

def test_gentle_pass_requires_grid_and_exact_replay():
    source=inspect.getsource(runner._extract_gentle)+inspect.getsource(runner.verify_gentle_bundle)
    assert 'score["status"] == "PASS" and replay["status"] == "PASS"' in source
    assert 'replay.get("status") != "PASS"' in source
