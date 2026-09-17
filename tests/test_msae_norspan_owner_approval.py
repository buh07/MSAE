"""Owner receipt integrity tests, NOT authentication of a human or production approval."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import copy
import hashlib
import importlib
import os
import pytest
from msae_norspan_controller_fixture import Fixture,n,r,c,approval
import msae_jumbo_pair_commit as j

PROOF={'channel':'owner_conversation','reference':'SYNTHETIC ONLY fixture; not owner enrollment','text':'SYNTHETIC ONLY approval test, never production authority'}


def module():return importlib.import_module('msae_norspan_owner_approval')


def raw_receipt(statement,*,decision='APPROVE',proof=None):
    value={'schema_version':'norspan_owner_approval_receipt_v1','owner_proof':copy.deepcopy(PROOF if proof is None else proof),'statement':statement}
    return b'# NORSPAN owner approval receipt v1\n\nDecision: '+decision.encode()+b'\n\n```json\n'+r.canonical_bytes(value)+b'\n```\n'


def whole(f,*,decision='APPROVE',proof=None,mutate=None):
    value=r._json(f.approvals.release);value['schema_version']='norspan_owner_approval_statement_v1'
    if mutate:mutate(value)
    raw=raw_receipt(value,decision=decision,proof=proof)
    return module().OwnerApprovals(f.root,release=raw,release_sha256=hashlib.sha256(raw).hexdigest())


def source(f,owner,*,mutate=None):
    value={'schema_version':'norspan_owner_approval_statement_v1','scope':'source_authority','verdict':'SHIP',
           'release_sha256':owner.release_sha256,'lineage_sha256':f.session.lineage,
           'authority_pair':j.receipt_record(f.session.expected('authority.json')),
           'review_sha256':hashlib.sha256((f.root/approval.AUTHORITY_REVIEW).read_bytes()).hexdigest()}
    if mutate:mutate(value)
    raw=raw_receipt(value);owner.bind_authority(raw,None,expected_sha256=hashlib.sha256(raw).hexdigest())
    return raw


def test_owner_whole_receipt_needs_no_signer_and_reuses_actual_subject_validation(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch)
    def forbidden(*args,**kwargs):raise AssertionError('owner mode requested digital signature')
    monkeypatch.setattr(approval,'verify_signature',forbidden)
    owner=whole(f);assert owner.verify_release()==f.root/approval.IMPLEMENTATION_REVIEW
    assert owner.authentication_method=='owner_origin_pinned_markdown'
    assert module().owner_receipt_bytes('APPROVE',proof=PROOF,statement=r._json(owner.release.split(b'```json\n')[1][:-5])['statement'])==owner.release


@pytest.mark.parametrize('decision',['PENDING','REJECT'])
def test_nonapproved_receipt_cannot_authorize(tmp_path,monkeypatch,decision):
    f=Fixture(tmp_path,monkeypatch)
    with pytest.raises(r.RuntimeBlocked):whole(f,decision=decision)


@pytest.mark.parametrize('fault',['agent_channel','unknown_channel','empty_reference','empty_text','control_reference','control_text','extra_field','missing_field','non_dict'])
def test_invalid_owner_proof_is_rejected(tmp_path,monkeypatch,fault):
    f=Fixture(tmp_path,monkeypatch);proof=copy.deepcopy(PROOF)
    if fault=='agent_channel':proof['channel']='agent_generated'
    elif fault=='unknown_channel':proof['channel']='unknown'
    elif fault=='empty_reference':proof['reference']=''
    elif fault=='empty_text':proof['text']=' '
    elif fault=='control_reference':proof['reference']='bad\nreference'
    elif fault=='control_text':proof['text']='bad\x00text'
    elif fault=='extra_field':proof['extra']='foreign'
    elif fault=='missing_field':proof.pop('reference')
    else:proof=[]
    with pytest.raises(r.RuntimeBlocked):whole(f,proof=proof)


@pytest.mark.parametrize('fault',['extra_object','duplicate_key','noncanonical','nonfinite','wrong_schema','wrong_scope','wrong_verdict','subject_float','subject_bool'])
def test_owner_receipt_strict_pin_grammar_schema_and_subject_types(tmp_path,monkeypatch,fault):
    f=Fixture(tmp_path,monkeypatch);stmt=r._json(f.approvals.release);stmt['schema_version']='norspan_owner_approval_statement_v1'
    if fault=='wrong_schema':stmt['schema_version']='norspan_signed_approval_v1'
    elif fault=='wrong_scope':stmt['scope']='source_authority'
    elif fault=='wrong_verdict':stmt['verdict']='BLOCK'
    elif fault in {'subject_float','subject_bool'}:stmt['subjects']['TODO.md']['bytes']=float(stmt['subjects']['TODO.md']['bytes']) if fault=='subject_float' else True
    raw=raw_receipt(stmt)
    if fault=='extra_object':raw+=b'foreign\n'
    elif fault=='duplicate_key':raw=raw.replace(b'"owner_proof":',b'"owner_proof":{},"owner_proof":',1)
    elif fault=='noncanonical':raw=raw.replace(b'{',b'{ ',1)
    elif fault=='nonfinite':raw=raw.replace(b'"owner_proof":',b'"owner_proof":NaN,"foreign":',1)
    with pytest.raises(r.RuntimeBlocked):module().OwnerApprovals(f.root,release=raw,release_sha256=hashlib.sha256(raw).hexdigest())


def test_owner_wrong_pin_blocks_before_any_candidate_read(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);stmt=r._json(f.approvals.release);stmt['schema_version']='norspan_owner_approval_statement_v1';raw=raw_receipt(stmt)
    def forbidden(*args,**kwargs):raise AssertionError('wrong receipt pin observed candidate')
    monkeypatch.setattr(c,'_CatalogReader',forbidden)
    with pytest.raises(r.RuntimeBlocked):module().OwnerApprovals(f.root,release=raw,release_sha256='0'*64)


def test_owner_source_receipt_binds_actual_pair_review_release_and_lineage(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);f.authority();owner=whole(f);source(f,owner)
    assert owner.verify_authority(f.session)==f.root/approval.AUTHORITY_REVIEW


@pytest.mark.parametrize('fault',['pair_float','wrong_release','wrong_lineage','review_drift','pair_drift'])
def test_owner_source_receipt_and_current_custody_faults_stop(tmp_path,monkeypatch,fault):
    f=Fixture(tmp_path,monkeypatch);f.authority();owner=whole(f)
    def mutation(value):
        if fault=='pair_float':value['authority_pair']['mode']=float(value['authority_pair']['mode'])
        elif fault=='wrong_release':value['release_sha256']='0'*64
        elif fault=='wrong_lineage':value['lineage_sha256']='0'*64
    with pytest.raises((r.RuntimeBlocked,j.PairFailure)):
        source(f,owner,mutate=mutation)
        if fault=='review_drift':(f.root/approval.AUTHORITY_REVIEW).write_bytes(b'foreign review retained\n')
        elif fault=='pair_drift':
            (n.PROV/'authority.json').chmod(0o600);(n.PROV/'authority.json').write_bytes(b'foreign authority retained\n');(n.PROV/'authority.json').chmod(0o644)
        owner.verify_authority(f.session)
    assert (n.PROV/'authority.json').exists()


@pytest.mark.parametrize('error',[OSError,KeyboardInterrupt])
def test_owner_admission_monitor_failure_releases_all_originals(tmp_path,monkeypatch,error):
    f=Fixture(tmp_path,monkeypatch);owner=whole(f);baseline=set(os.listdir('/proc/self/fd'))
    monitor=os.stat('/proc/self/fd');realclose=os.close;fired=[]
    def close(fd):
        info=os.fstat(fd);realclose(fd)
        if (info.st_dev,info.st_ino)==(monitor.st_dev,monitor.st_ino):fired.append(True);raise error('synthetic owner monitor close')
    monkeypatch.setattr(os,'close',close)
    with pytest.raises(error):owner.verify_release()
    assert fired and set(os.listdir('/proc/self/fd'))==baseline


def transport(f,owner,*,with_source):
    paths={}
    values={'release_approval':owner.release}
    if with_source:values['authority_approval']=owner._authority[0]
    for name,raw in values.items():
        path=f.external/('owner-'+name+'.md');path.write_bytes(raw);path.chmod(0o644);paths[name]=str(path)
    return SimpleNamespace(approval_kind='owner-markdown',approval_key=None,approval_key_sha256=None,release_signature=None,authority_signature=None,
        authority_approval=paths.get('authority_approval'),authority_approval_sha256=owner._authority[2] if with_source else None,
        release_approval=paths['release_approval'],release_sha256=owner.release_sha256,lineage_sha256=f.session.lineage,
        outside_catalog=str(f.store.path),catalog_sha256=f.store.sha256)


@pytest.mark.parametrize('with_source',[False,True])
def test_owner_transport_uses_actual_receipts_and_pinned_catalog(tmp_path,monkeypatch,with_source):
    f=Fixture(tmp_path,monkeypatch)
    if with_source:f.authority()
    owner=whole(f)
    if with_source:source(f,owner)
    controller=c.from_arguments(transport(f,owner,with_source=with_source))
    assert controller.approvals.authentication_method=='owner_origin_pinned_markdown'
    assert controller.catalog.sha256==f.store.sha256
    if with_source:assert controller.approvals.verify_authority(controller.session)==f.root/approval.AUTHORITY_REVIEW


@pytest.mark.parametrize('field',['approval_key','approval_key_sha256','release_signature','authority_signature'])
def test_owner_transport_rejects_mixed_signed_arguments_before_reads(tmp_path,monkeypatch,field):
    f=Fixture(tmp_path,monkeypatch);owner=whole(f);args=transport(f,owner,with_source=False);setattr(args,field,'foreign')
    def forbidden(*args,**kwargs):raise AssertionError('mixed arguments observed input')
    monkeypatch.setattr(r,'read_ordinary_file',forbidden)
    with pytest.raises(r.RuntimeBlocked,match='owner_approval_mixed_signature_arguments'):c.from_arguments(args)


@pytest.mark.parametrize('path',['release_approval','authority_approval'])
def test_owner_each_transport_path_admits_pressure_before_observing_input(tmp_path,monkeypatch,path):
    f=Fixture(tmp_path,monkeypatch);f.authority();owner=whole(f);source(f,owner);args=transport(f,owner,with_source=True)
    baseline=set(os.listdir('/proc/self/fd'));original=c._placement;realopen=os.open;realclose=os.close;fillers=[];subjects=[];peaks=[];filled=[]
    def placement(actual,*values,**kwargs):
        result=original(actual,*values,**kwargs)
        if actual==Path(getattr(args,path)):
            for _ in range(4090-r._current_fd_count()):fillers.append(realopen('/dev/null',os.O_RDONLY))
            assert r._current_fd_count()==4090;filled.append(path)
        return result
    def opening(actual,*values,**kwargs):
        fd=realopen(actual,*values,**kwargs)
        if filled:
            peaks.append(len(os.listdir('/proc/self/fd'))-1)
            if str(actual)!='/proc/self/fd':subjects.append(str(actual))
        return fd
    monkeypatch.setattr(c,'_placement',placement);monkeypatch.setattr(os,'open',opening)
    try:
        with pytest.raises(r.RuntimeBlocked,match='observation_fd_admission'):c.from_arguments(args)
    finally:
        for fd in fillers:realclose(fd)
    assert filled==[path] and not subjects and peaks and max(peaks)<=4096 and set(os.listdir('/proc/self/fd'))==baseline


@pytest.mark.parametrize('kind',['owner-markdown','ed25519'])
def test_real_guard_stops_both_modes_before_any_input_or_monitor(monkeypatch,kind):
    def forbidden(*args,**kwargs):raise AssertionError('production owner transport guard observed input')
    monkeypatch.setattr(r,'read_ordinary_file',forbidden);monkeypatch.setattr(r,'admit_observation_fds',forbidden);monkeypatch.setattr(c,'_placement',forbidden)
    with pytest.raises(n.GateFailure,match='jpc_whole_qualification_pending'):c.from_arguments(SimpleNamespace(approval_kind=kind))


def test_cli_owner_mode_requires_no_digital_key_or_signature():
    parser=argparse.ArgumentParser();c.add_arguments(parser)
    args=parser.parse_args(['--release-approval','/jumbo/synthetic-owner.md','--release-sha256','0'*64,
                           '--lineage-sha256','f'*64,'--outside-catalog','/jumbo/synthetic-catalog','--catalog-sha256','0'*64])
    assert args.approval_kind=='owner-markdown' and args.approval_key is None and args.release_signature is None


def test_owner_actual_fresh_scientific_terminal_recovery_is_not_signed_or_launch_authority(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);f.acquire(monkeypatch);owner=whole(f);source(f,owner)
    f.approvals=owner;f.controller=c.Controller(f.session,f.store,owner)
    f.controller.execute('prepare');before=len(f.calls)
    observed=f.fresh().execute('recover')
    assert observed['status']=='verified_current_observation_not_launch_authority'
    assert observed['approval_verified'] is True and observed['signed_approval_verified'] is False
    assert observed['approval_authentication_method']=='owner_origin_pinned_markdown'
    assert observed['production_canonical_authority_established'] is False and observed['source_work_authorized'] is False
    assert observed['terminal_raw_reconstruction_attempts']==1 and observed['C2_scientific_opens']==0 and len(f.calls)==before
    assert observed['historical_scratch_bytes_attested'] is False and n._RECOVERY_COUNTS.get() is None
