"""Actual synthetic history/acquisition/science/terminal validators, no models."""
from msae_norspan_controller_fixture import Fixture,n
import pytest

def test_actual_controller_builds_history_and_fresh_authority(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);f.authority()
    fresh=f.fresh()
    with n.paired_control_session(fresh.session):
        n.validate_authority_chain()
        assert n.classify_protocol_state()=='authority'

def test_actual_controller_acquisition_and_scientific_terminal(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);f.acquire(monkeypatch)
    assert len(f.calls)==8
    fresh=f.fresh();fresh.execute('prepare')
    fresh=f.fresh();fresh.execute('verify')
    with n.paired_control_session(fresh.session):assert n.classify_protocol_state()=='scientific_terminal'
    assert len(f.calls)==8


def test_fresh_baseline_full_history_recovery_does_not_authorize(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);f.history()
    result=f.fresh().execute('recover')
    assert result['state']=='baseline'
    assert result['history_replayed'] is True
    assert result['source_work_authorized'] is False
    assert result['historical_success_inferred'] is False
    assert 'network_operations' not in result
    assert result['source_network_operations']==0
    assert result['operation_scope']=='controller_direct_calls_only_not_status_helpers'
    assert result['status_helper_effects']=='UNVERIFIED'
    assert result['status_protected_content_exclusion']=='UNVERIFIED'
    assert result['status_network_isolation']=='UNVERIFIED'


@pytest.mark.parametrize('terminal',['acquisition','success','science_rejection','acquisition_rejection'])
def test_fresh_full_recovery_actual_terminal_reconstruction(tmp_path,monkeypatch,terminal):
    f=Fixture(tmp_path,monkeypatch)
    if terminal=='acquisition_rejection':
        with pytest.raises(n.GateFailure,match='source_acquisition_clone'):f.acquire(monkeypatch,failure='clone')
    else:
        f.acquire(monkeypatch,license_bytes=b'unacceptable synthetic terms\n' if terminal=='science_rejection' else None)
        if terminal=='science_rejection':
            with pytest.raises(n.ScientificGateFailure):f.fresh().execute('prepare')
        elif terminal=='success':f.fresh().execute('prepare')
    count=len(f.calls)
    fresh=f.fresh();result=fresh.execute('recover')
    assert len(f.calls)==count
    assert result['source_acquisition_commands']==result['model_operations']==0
    assert result['source_work_authorized'] is False and result['historical_success_inferred'] is False
    assert result['terminal_raw_reconstruction_attempts']==(1 if terminal in {'success','science_rejection'} else 0)
    assert result['C2_scientific_opens']==0
    assert result['local_status_observation_attempts']==result['local_status_observation_completed']>0
