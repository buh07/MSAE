"""Actual synthetic metadata recovery, expressly NOT full/approved recovery."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r
import msae_norspan_jpc_controls as c
import prepare_msae_independent_norspan_v1 as p

def fixture(tmp_path,monkeypatch):
    root=tmp_path/'controls';root.mkdir(mode=0o755);root.chmod(0o755)
    session=c.ControlSession(root,lineage_sha256='a'*64)
    evidence={'process':{'scanned_process_count':1,'prohibited_match_count':0,'matches':[]},'training':{'entry_count':0,'manifest_sha256':'0'*64},'porcelain':{'outside_protocol_count':0,'outside_protocol_sha256':'0'*64},'model_operations':0,'gpu_queries':0,'training_runs':0}
    def publish(name,value):session.register(name,j.create_pair(root/name,r.canonical_bytes(value)+b'\n',mode=0o644))
    publish('current_history_registry.json',{'schema_version':'msae_independent_norspan_v1_current_history_registry_v1','status':'synthetic_metadata_fixture_not_census'})
    publish('baseline.json',{'schema_version':'msae_independent_norspan_v1_baseline_v1','current_history_registry_sha256':session.expected('current_history_registry.json').sha256,'config_sha256':'0'*64,'implementation_review_sha256':'1'*64,'git_head':'1'*40,'evidence':evidence,'source_namespace_absent_at_registry_start':True,'model_operations':0,'gpu_queries':0,'training_runs':0,'status':'eligible'})
    publish('authority.json',{'schema_version':'msae_independent_norspan_v1_authority_v1','source_repo':p.REPO,'source_commit':p.COMMIT,'source_files':[*p.SOURCE_FILES.values(),p.LICENSE_FILE],'baseline_sha256':session.expected('baseline.json').sha256,'current_history_registry_sha256':session.expected('current_history_registry.json').sha256,'controls':{},'pre_authority_evidence':evidence,'pre_authority_history_census':{},'absent_at_publication':[],'model_operations':0,'gpu_queries':0,'training_runs':0,'status':'awaiting_independent_authority_review'})
    with r.reserve_scratch(tmp_path/'retained',authority_sha256=session.expected('authority.json').sha256,entry_lineage_sha256='a'*64) as lease:binding=dict(lease.binding)
    entry={key:{} for key in p.CONTROL_FIELDS['acquisition_entry.json']}
    entry.update(schema_version='msae_independent_norspan_v1_acquisition_entry_jpc_v1',source_repo=p.REPO,source_commit=p.COMMIT,source_files=[*p.SOURCE_FILES.values(),p.LICENSE_FILE],baseline_sha256=session.expected('baseline.json').sha256,history_registry_sha256=session.expected('current_history_registry.json').sha256,authority_sha256=session.expected('authority.json').sha256,authority_review_sha256='2'*64,scratch_binding=binding,entry_lineage_sha256='a'*64,pre_entry_evidence=evidence,status='entered',subprocesses_started=0,model_operations=0,gpu_queries=0,training_runs=0)
    publish('acquisition_entry.json',entry)
    publish('pre_network_ready.json',{'schema_version':'msae_independent_norspan_v1_pre_network_ready_jpc_v1','acquisition_entry_sha256':session.expected('acquisition_entry.json').sha256,'scratch_binding':binding,'evidence':evidence,'history_census':{},'status':'ready'})
    return session,publish,binding,evidence

def recover(session):return c.recover_application_metadata(session,expected_implementation_sha256='1'*64,expected_authority_review_sha256='2'*64)

def test_prestart_paired_typed_lineage_retained_scratch_never_authorizes(tmp_path,monkeypatch):
    session,_publish,binding,_evidence=fixture(tmp_path,monkeypatch)
    result=recover(session)
    assert result['status']=='prestart_metadata_observed_pending_full_validation'
    assert result['canonical_authority']=='NOT_ESTABLISHED' and result['history_science_replay']=='NOT_COMPLETED'
    assert result['source_operations']==result['model_operations']==0 and result['source_work_authorized'] is False
    assert result['scratch']['retained'] is True and Path(binding['path']).exists()

@pytest.mark.parametrize('kind',['partial_started','complete_started','scratch_foreign','wrong_implementation'])
def test_recovery_blockers_retain_no_repeated_work(tmp_path,monkeypatch,kind):
    session,publish,binding,evidence=fixture(tmp_path,monkeypatch)
    if kind=='partial_started':(session.root/'.network_started.json.stage').write_bytes(b'partial')
    elif kind=='complete_started':publish('network_started.json',{'schema_version':'msae_independent_norspan_v1_network_started_jpc_v1','pre_network_ready_sha256':session.expected('pre_network_ready.json').sha256,'scratch_binding':binding,'evidence':evidence,'history_census':{},'status':'started'})
    elif kind=='scratch_foreign':(Path(binding['path'])/'home'/'foreign').write_bytes(b'retained')
    with pytest.raises((r.RuntimeBlocked,p.GateFailure,j.PairFailure)):
        if kind=='wrong_implementation':c.recover_application_metadata(session,expected_implementation_sha256='9'*64,expected_authority_review_sha256='2'*64)
        else:recover(session)
    assert Path(binding['path']).exists() and list(session.root.iterdir())
