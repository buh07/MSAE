"""Named controller fault cells; whole closure is not inferred from test totals."""
from pathlib import Path
import copy
import hashlib
import os
import resource
import pytest
from msae_norspan_controller_fixture import Fixture,n,r,c,approval,_eligible_synthetic_source,_install_synthetic_git
import msae_jumbo_pair_commit as j


@pytest.mark.parametrize('timing',['entry','after_directory'])
def test_actual_controller_aggregate_pressure_blocks_without_overflow_or_leaks(tmp_path,monkeypatch,timing):
    f=Fixture(tmp_path,monkeypatch)
    n.PROV.mkdir(parents=True,mode=0o755);n.PROV.chmod(0o755)
    f.session.register('baseline.json',j.create_pair(n.PROV/'baseline.json',b'{}\n',mode=0o644))
    n.DATA.mkdir(parents=True,mode=0o700);n.DATA.chmod(0o700);(n.DATA/'raw').mkdir(mode=0o700)
    f.session.raw_manifest=r.publish_flat_pairs(n.RAW,{name:b'opaque synthetic raw' for name in [*n.SOURCE_FILES.values(),n.LICENSE_FILE]},directory_mode=0o555,file_mode=0o444)
    f.session.private_manifest=r.publish_role_pairs(n.PRIVATE,{role:b'opaque synthetic role' for role in r.ROLES})
    f.session.checkpoint()
    baseline=set(os.listdir('/proc/self/fd'));realopen=os.open;original=r._directory
    fillers=[];peaks=[];filled=[]
    def fill():
        for _ in range(4031-r._current_fd_count()):fillers.append(realopen('/dev/null',os.O_RDONLY))
        assert r._current_fd_count()==4031
        filled.append(True)
    def opening(*args,**kwargs):
        fd=realopen(*args,**kwargs);peaks.append(len(os.listdir('/proc/self/fd')));return fd
    def directory(*args,**kwargs):
        owned=original(*args,**kwargs)
        if not filled:fill()
        return owned
    monkeypatch.setattr(os,'open',opening)
    if timing=='after_directory':monkeypatch.setattr(r,'_directory',directory)
    else:fill()
    try:
        with n.paired_control_session(f.session),pytest.raises(r.RuntimeBlocked,match='observation_fd_admission'):
            f.controller.validate_current_custody(durable=True)
    finally:
        for fd in fillers:os.close(fd)
    assert filled==[True] and peaks and max(peaks)<=4096
    assert set(os.listdir('/proc/self/fd'))==baseline
    assert (n.PRIVATE/'c2'/'payload.jsonl').exists() and (n.PROV/'baseline.json').stat().st_nlink==2


@pytest.mark.parametrize('consumer',['reader','writer','create','load','release','signature'])
def test_actual_catalog_release_signature_pressure_stops_before_unsafe_subjects(tmp_path,monkeypatch,consumer):
    f=Fixture(tmp_path,monkeypatch)
    baseline=set(os.listdir('/proc/self/fd'));fillers=[];peaks=[];subjects=[]
    realopen=os.open;realmemfd=os.memfd_create
    def opening(path,*args,**kwargs):
        fd=realopen(path,*args,**kwargs);peaks.append(len(os.listdir('/proc/self/fd')))
        if path!='/proc/self/fd':subjects.append(str(path))
        return fd
    def memfd(*args,**kwargs):
        subjects.append('memfd');return realmemfd(*args,**kwargs)
    for _ in range(4090-r._current_fd_count()):fillers.append(realopen('/dev/null',os.O_RDONLY))
    monkeypatch.setattr(os,'open',opening);monkeypatch.setattr(os,'memfd_create',memfd)
    try:
        with pytest.raises(r.RuntimeBlocked,match='observation_fd_admission'):
            if consumer=='reader':
                owned=c._CatalogReader(f.store.path,f.store.sha256)
                try:owned.validate()
                finally:owned.close()
            elif consumer=='writer':f.session.checkpoint()
            elif consumer=='create':c.CatalogStore.create(f.external/'new-catalog',n.PROV,project_root=n.ROOT,lineage_sha256='f'*64)
            elif consumer=='load':c.CatalogStore.load(f.store.path,expected_sha256=f.store.sha256,root=n.PROV,project_root=n.ROOT,lineage_sha256='f'*64)
            elif consumer=='release':f.approvals.verify_release()
            else:approval.verify_signature(f.key,f.approvals.release,f.approvals.release_signature,key_sha256=hashlib.sha256(f.key).hexdigest())
    finally:
        for fd in fillers:os.close(fd)
    assert not subjects and peaks and max(peaks)<=4096
    assert set(os.listdir('/proc/self/fd'))==baseline
    assert not (f.external/'new-catalog').exists() and not (f.store.root/'catalog-000001.json').exists()


def test_actual_typed_full_recovery_blocks_transient_aggregate_fd_growth(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);f.authority()
    baseline=set(os.listdir('/proc/self/fd'));realopen=os.open;original=c.Controller.validate_current_custody
    peaks=[];calls=[]
    def custody(self,*,durable):
        fillers=[];calls.append(True)
        try:
            for _ in range(4050-r._current_fd_count()):fillers.append(realopen('/dev/null',os.O_RDONLY))
            assert r._current_fd_count()==4050
            return original(self,durable=durable)
        finally:
            for fd in fillers:os.close(fd)
    def opening(*args,**kwargs):
        fd=realopen(*args,**kwargs);peaks.append(len(os.listdir('/proc/self/fd')));return fd
    monkeypatch.setattr(c.Controller,'validate_current_custody',custody);monkeypatch.setattr(os,'open',opening)
    with pytest.raises(r.RuntimeBlocked,match='observation_fd_admission'):f.fresh().execute('recover')
    assert calls==[True] and peaks and max(peaks)<=4096
    assert set(os.listdir('/proc/self/fd'))==baseline and n._RECOVERY_COUNTS.get() is None


@pytest.mark.parametrize('timing',['before_leaf','after_leaf'])
@pytest.mark.parametrize('reader',['classify','bytes','prefix','digest','preopened'])
def test_actual_absolute_history_headroom_blocks_before_unsafe_consumer(tmp_path,monkeypatch,timing,reader):
    assert resource.getrlimit(resource.RLIMIT_NOFILE)[0] > 4200
    root=tmp_path/'synthetic-deep-history';root.mkdir();leaf=root
    for index in range(64):leaf=leaf/f'd{index}';leaf.mkdir()
    path=leaf/'ordinary.txt';path.write_bytes(b'synthetic ordinary history\n')
    monkeypatch.setattr(n,'ROOT',root)
    baseline=set(os.listdir('/proc/self/fd'));fillers=[];observed=[];parent=None
    realopen=os.open;inode=path.stat().st_ino
    def opening(*args,**kwargs):
        fd=realopen(*args,**kwargs)
        if os.fstat(fd).st_ino==inode:observed.append(r._current_fd_count())
        return fd
    monkeypatch.setattr(os,'open',opening)
    if reader=='preopened':parent=n._open_parent_fd(path)
    def fill():
        for _ in range(4031-r._current_fd_count()):fillers.append(realopen('/dev/null',os.O_RDONLY))
        assert r._current_fd_count()==4031
    try:
        with pytest.raises(n.GateFailure,match='history_fd_admission'):
            with n._history_census() as walker:
                for row in walker:
                    if timing=='before_leaf' and row[0].count('/')==63 and row[3]=='public_directory_lstat_only':fill()
                    if row[0].endswith('ordinary.txt'):
                        if timing=='after_leaf':fill()
                        if reader=='classify':n.classify_file(row[1],row[2])
                        elif reader=='bytes':n.read_bytes_nofollow(row[1])
                        elif reader=='prefix':n.read_prefix_nofollow(row[1],2)
                        elif reader=='digest':n.stream_file_digest(row[1])
                        else:n.read_bytes_nofollow(row[1],parent_fd=parent)
    finally:
        if parent is not None:n._close_parent_fd(parent)
        for fd in fillers:os.close(fd)
    assert set(os.listdir('/proc/self/fd'))==baseline
    assert not observed or max(observed)<=4096


@pytest.mark.parametrize('reader',['bytes','prefix','digest'])
def test_actual_paired_early_reader_rechecks_caller_descriptor_growth(tmp_path,monkeypatch,reader):
    from msae_norspan_jpc_controls import ControlSession
    prov=tmp_path/'synthetic-controls';prov.mkdir();prov.chmod(0o755)
    monkeypatch.setattr(n,'PROV',prov)
    session=ControlSession(prov,lineage_sha256='f'*64)
    receipt=j.create_pair(prov/'baseline.json',b'{}\n',mode=0o644)
    session.register('baseline.json',receipt)
    baseline=set(os.listdir('/proc/self/fd'));fillers=[];realopen=os.open;unsafe=[]
    def opening(path,*args,**kwargs):
        if path in {'baseline.json','.baseline.json.stage'}:unsafe.append(path)
        return realopen(path,*args,**kwargs)
    monkeypatch.setattr(os,'open',opening)
    try:
        for _ in range(4090-r._current_fd_count()):fillers.append(realopen('/dev/null',os.O_RDONLY))
        with n.paired_control_session(session),pytest.raises(n.GateFailure,match='history_fd_admission'):
            if reader=='bytes':n.read_bytes_nofollow(prov/'baseline.json')
            elif reader=='prefix':n.read_prefix_nofollow(prov/'baseline.json',2)
            else:n.stream_file_digest(prov/'baseline.json')
    finally:
        for fd in fillers:os.close(fd)
    assert not unsafe and set(os.listdir('/proc/self/fd'))==baseline


@pytest.mark.parametrize('fault',['unsigned','wrong_scope','wrong_verdict','missing_dependency','extra_subject','wrong_mode','bool_bytes','noncanonical','duplicate','wrong_release_pin','stale_subject','subject_alias'])
def test_signed_candidate_faults_cannot_establish_canonical_binding(tmp_path,monkeypatch,fault):
    f=Fixture(tmp_path,monkeypatch)
    value=r._json(f.approvals.release)
    pin=None
    if fault=='wrong_scope':value['scope']='source_authority'
    elif fault=='wrong_verdict':value['verdict']='BLOCK'
    elif fault=='missing_dependency':value['subjects'].pop('scripts/msae_norspan_jpc_controls.py')
    elif fault=='extra_subject':value['subjects']['unapproved.py']=next(iter(value['subjects'].values()))
    elif fault=='wrong_mode':value['subjects']['scripts/msae_norspan_jpc_controller.py']['mode']=0o644
    elif fault=='bool_bytes':value['subjects']['TODO.md']['bytes']=True
    elif fault=='stale_subject':(f.root/'TODO.md').write_bytes(b'synthetic stale subject')
    elif fault=='subject_alias':os.link(f.root/'TODO.md',f.external/'foreign-link')
    raw,sig=f.sign(value)
    if fault=='unsigned':sig=b'0'*64
    elif fault=='wrong_release_pin':pin='0'*64
    elif fault in {'noncanonical','duplicate'}:
        raw = b' '+raw if fault=='noncanonical' else raw[:-2]+b',"verdict":"SHIP"}\n'
        # Sign genuinely invalid canonical/schema bytes, not a bad-signature proxy.
        path=f.external/'bad-statement.json';path.write_bytes(raw)
        sigpath=f.external/'bad-signature.bin'
        approval.subprocess.run(['/usr/bin/openssl','pkeyutl','-sign','-rawin','-inkey',str(f.private),'-in',str(path),'-out',str(sigpath)],check=True,capture_output=True)
        sig=sigpath.read_bytes()
    with pytest.raises((r.RuntimeBlocked,n.GateFailure)):
        approval.Approvals(f.root,key=f.key,key_sha256=hashlib.sha256(f.key).hexdigest(),release=raw,release_signature=sig,release_sha256=pin or hashlib.sha256(raw).hexdigest())
    assert not n.DATA.exists() and not n.PROV.exists()


@pytest.mark.parametrize('marker',['current_history_registry.json','baseline.json','authority.json','acquisition_entry.json','pre_network_ready.json','network_started.json','scientific_entry.json','pre_raw_ready.json','raw_access_started.json','source_acquisition.json','seal.json'])
@pytest.mark.parametrize('exception',[OSError,KeyboardInterrupt])
def test_actual_marker_checkpoint_faults_retain_evidence_and_stop_access(tmp_path,monkeypatch,marker,exception):
    f=Fixture(tmp_path,monkeypatch)
    original=c._write_snapshot
    fired=[]
    def fail(path,raw,names):
        value=r._json(raw)
        if marker in value['catalog']['controls']:
            fired.append(marker)
            raise exception('synthetic checkpoint fault:'+marker)
        return original(path,raw,names)
    monkeypatch.setattr(c,'_write_snapshot',fail)
    calls=[]
    with pytest.raises(exception):
        if marker in {'current_history_registry.json','baseline.json'}:f.history()
        elif marker=='authority.json':f.authority()
        else:
            f.authority();calls=_install_synthetic_git(monkeypatch,_eligible_synthetic_source())
            f.controller.execute('acquire')
            f.controller.execute('prepare')
    assert fired==[marker]
    assert (n.PROV/marker).exists() and (n.PROV/('.'+marker+'.stage')).exists()
    assert (n.PROV/marker).stat().st_nlink==2
    if marker in {'acquisition_entry.json','pre_network_ready.json','network_started.json'}:assert calls==[]
    if marker in {'scientific_entry.json','pre_raw_ready.json','raw_access_started.json'}:
        assert len(calls)==8
        assert not (n.PROV/'source_manifest.json').exists()
    with pytest.raises((r.RuntimeBlocked,n.GateFailure)):
        f.fresh().execute('recover')
    assert (n.PROV/marker).exists()


@pytest.mark.parametrize('walker',['history','inventory'])
@pytest.mark.parametrize('axis',['objects','depth'])
def test_bounded_census_overflow_blocks_without_silently_skipping(tmp_path,monkeypatch,walker,axis):
    root=tmp_path/'synthetic-tree';root.mkdir()
    monkeypatch.setattr(n,'ROOT',root)
    if axis=='objects':
        monkeypatch.setattr(r,'ENTRY_LIMIT',2)
        for i in range(3):(root/str(i)).write_bytes(b'synthetic')
    else:
        p=root
        for i in range(65):p=p/'d';p.mkdir()
    with pytest.raises((r.RuntimeBlocked,n.GateFailure)):
        list(n._history_objects()) if walker=='history' else n._descriptor_tree(root)
    assert root.exists()


@pytest.mark.parametrize('fault',['ordinary_addition','empty_directory','binary_addition','frozen_hash','scratch_extra','public_extra','private_extra','third_alias'])
def test_actual_full_recovery_rejects_mutations_and_retains_foreign_evidence(tmp_path,monkeypatch,fault):
    f=Fixture(tmp_path,monkeypatch);f.acquire(monkeypatch)
    if fault in {'private_extra','third_alias'}:f.controller.execute('prepare')
    if fault=='ordinary_addition':(f.root/'new-history.txt').write_bytes(b'unfrozen synthetic history')
    elif fault=='empty_directory':(f.root/'new-empty-directory').mkdir()
    elif fault=='binary_addition':(f.root/'unknown-binary.dat').write_bytes(b'\xff\x00')
    elif fault=='frozen_hash':(f.root/'TODO.md').write_bytes(b'synthetic changed frozen subject')
    elif fault=='scratch_extra':
        with n.paired_control_session(f.session):binding=f.session.canonical('acquisition_entry.json')['scratch_binding']
        (Path(binding['path'])/'foreign-retained').write_bytes(b'do not erase')
    elif fault=='public_extra':(n.PROV/'foreign-control').write_bytes(b'do not erase')
    elif fault=='private_extra':(n.PRIVATE/'c2'/'foreign').write_bytes(b'do not erase')
    else:os.link(n.PRIVATE/'c2'/'payload.jsonl',f.external/'third-link')
    count=len(f.calls)
    with pytest.raises((r.RuntimeBlocked,n.GateFailure,j.PairFailure)):f.fresh().execute('recover')
    assert len(f.calls)==count and n.RAW.exists()
    assert len(list(n.RAW.iterdir()))==8


@pytest.mark.parametrize('numeric',['float','bool'])
def test_genuinely_signed_authority_receipt_requires_exact_integer_schema(tmp_path,monkeypatch,numeric):
    f=Fixture(tmp_path,monkeypatch);f.authority()
    value=r._json(f.approvals._authority[0])
    for key in ['device','inode','mode','byte_count']:
        value['authority_pair'][key]=float(value['authority_pair'][key]) if numeric=='float' else True
    raw,sig=f.sign(value)
    with pytest.raises((r.RuntimeBlocked,j.PairFailure)):
        f.approvals.bind_authority(raw,sig,expected_sha256=hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize('fault',['earlier_file_bytes','earlier_directory_extra'])
def test_history_last_yield_cannot_hide_earlier_object_drift(tmp_path,monkeypatch,fault):
    root=tmp_path/'synthetic-history';root.mkdir();(root/'a').mkdir()
    (root/'a'/'early.txt').write_bytes(b'old bytes')
    (root/'z-last.txt').write_bytes(b'late synthetic file')
    monkeypatch.setattr(n,'ROOT',root)
    walker=n._history_objects();seen=[]
    for row in walker:
        seen.append(row[0])
        if row[0]=='z-last.txt':
            if fault=='earlier_file_bytes':(root/'a'/'early.txt').write_bytes(b'new bytes')
            else:(root/'a'/'foreign').write_bytes(b'retain me')
            break
    with pytest.raises((n.GateFailure,r.RuntimeBlocked,j.PairFailure)):list(walker)
    assert 'z-last.txt' in seen
    assert (root/'a'/'early.txt').exists()


def test_real_bounded_local_status_evidence_is_separately_counted(tmp_path,monkeypatch):
    root=tmp_path/'synthetic-status';root.mkdir()
    env={'PATH':'/usr/bin:/bin','HOME':str(tmp_path),'LC_ALL':'C','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'}
    approval.subprocess.run(['/usr/bin/git','init','-q',str(root)],check=True,capture_output=True,env=env)
    (root/'ordinary.txt').write_bytes(b'synthetic public history')
    monkeypatch.setattr(n,'ROOT',root)
    monkeypatch.setattr(n,'_process_snapshot',lambda:{'scanned_process_count':1,'prohibited_match_count':0,'matches':[]})
    counts={'local_status_observation_attempts':0,'local_status_observation_completed':0,'terminal_raw_reconstruction_attempts':0}
    token=n._RECOVERY_COUNTS.set(counts)
    try:
        evidence=n.evidence_snapshot()
        assert evidence['porcelain']['outside_protocol_count']==1
        assert counts['local_status_observation_attempts']==counts['local_status_observation_completed']==1
    finally:n._RECOVERY_COUNTS.reset(token)


@pytest.mark.parametrize('error',[OSError,KeyboardInterrupt])
def test_local_status_attempt_failure_is_not_falsely_counted_as_zero(tmp_path,monkeypatch,error):
    monkeypatch.setattr(n,'_process_snapshot',lambda:{'scanned_process_count':1,'prohibited_match_count':0,'matches':[]})
    def fail():raise error('synthetic status failure')
    monkeypatch.setattr(n,'_git_porcelain_snapshot',fail)
    counts={'local_status_observation_attempts':0,'local_status_observation_completed':0,'terminal_raw_reconstruction_attempts':0}
    token=n._RECOVERY_COUNTS.set(counts)
    try:
        with pytest.raises(error):n.evidence_snapshot()
        assert counts['local_status_observation_attempts']==1 and counts['local_status_observation_completed']==0
    finally:n._RECOVERY_COUNTS.reset(token)


@pytest.mark.parametrize('consumer',['build','validate'])
@pytest.mark.parametrize('close_fault',[False,True])
def test_history_consumer_failure_closes_retained_generator_immediately(tmp_path,monkeypatch,consumer,close_fault):
    f=Fixture(tmp_path,monkeypatch)
    cfg=n.load_config()
    root=tmp_path/'small-public-history';root.mkdir();(root/'ordinary.txt').write_bytes(b'synthetic public text')
    monkeypatch.setattr(n,'ROOT',root)
    registry=n.build_history_registry(cfg)
    retained=[];original=n._history_objects
    def census():
        walker=original();retained.append(walker);return walker
    monkeypatch.setattr(n,'_history_objects',census)
    primary=RuntimeError('synthetic consumer failure')
    def fail(*args,**kwargs):raise primary
    monkeypatch.setattr(n,'classify_file',fail)
    before=set(os.listdir('/proc/self/fd'))
    original_close=os.close;replacements=[];fired=[]
    inode=(root/'ordinary.txt').stat().st_ino
    def close(fd):
        info=os.fstat(fd);original_close(fd)
        if close_fault and info.st_ino==inode and not fired:
            fired.append(fd)
            replacement=os.open('/dev/null',os.O_RDONLY);replacements.append(replacement)
            assert replacement==fd
            raise OSError('synthetic post-release close fault')
    monkeypatch.setattr(os,'close',close)
    try:
        with pytest.raises(RuntimeError) as caught:
            n.build_history_registry(cfg) if consumer=='build' else n.validate_history_registry(registry,cfg)
        assert caught.value is primary
        assert retained and retained[0].gi_frame is None
        if close_fault:
            assert fired and getattr(primary,'__notes__',[])
            assert all(os.fstat(fd) for fd in replacements)
    finally:
        for fd in replacements:original_close(fd)
    assert set(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('boundary',['network','raw'])
def test_full_fresh_recovery_never_retries_started_incomplete_work(tmp_path,monkeypatch,boundary):
    f=Fixture(tmp_path,monkeypatch);f.authority()
    calls=_install_synthetic_git(monkeypatch,_eligible_synthetic_source())
    if boundary=='network':
        import acquire_msae_independent_norspan_v1 as a
        original=a.run
        def interrupt(argv,**kwargs):
            if 'clone' in argv:raise KeyboardInterrupt('synthetic initiated clone interruption')
            return original(argv,**kwargs)
        monkeypatch.setattr(a,'run',interrupt)
        command='acquire'
    else:
        f.controller.execute('acquire')
        def interrupt(*args,**kwargs):raise KeyboardInterrupt('synthetic initiated raw interruption')
        monkeypatch.setattr(n,'load_validated_raw',interrupt)
        command='prepare'
    with pytest.raises(KeyboardInterrupt):f.controller.execute(command)
    marker='network_started.json' if boundary=='network' else 'raw_access_started.json'
    assert (n.PROV/marker).exists() and not (n.PROV/'rejection.json').exists() and not (n.PROV/'seal.json').exists()
    before=len(calls)
    with pytest.raises(r.RuntimeBlocked,match='started_without_terminal_no_retry'):f.fresh().execute('recover')
    assert len(calls)==before and (n.PROV/marker).exists()


@pytest.mark.parametrize('exit_kind',['exhaust','close','throw'])
def test_history_never_reads_excluded_bytes_and_releases_originals(tmp_path,monkeypatch,exit_kind):
    root=tmp_path/'synthetic-protected-history';root.mkdir()
    (root/'private').mkdir();(root/'private'/'fake-private-marker').write_bytes(b'synthetic excluded private marker')
    (root/'model.pt').write_bytes(b'synthetic excluded model')
    (root/'ordinary.txt').write_bytes(b'synthetic public bytes')
    forbidden={(root/'model.pt').stat().st_ino,(root/'private'/'fake-private-marker').stat().st_ino}
    monkeypatch.setattr(n,'ROOT',root)
    original=os.pread
    def protected_read(fd,*args):
        assert os.fstat(fd).st_ino not in forbidden,'excluded content was opened for hashing'
        return original(fd,*args)
    monkeypatch.setattr(os,'pread',protected_read)
    before=set(os.listdir('/proc/self/fd'))
    walker=n._history_objects()
    if exit_kind=='exhaust':list(walker)
    else:
        next(walker)
        if exit_kind=='close':walker.close()
        else:
            with pytest.raises(KeyboardInterrupt):walker.throw(KeyboardInterrupt('synthetic throw'))
    assert set(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('walker',['history','inventory'])
@pytest.mark.parametrize('kind',['directory','file','symlink'])
def test_credential_namespace_blocks_history_without_exemption_or_content_access(tmp_path,monkeypatch,walker,kind):
    root=tmp_path/'synthetic-credential-stop';root.mkdir()
    (root/'a-before.txt').write_bytes(b'earlier synthetic public object')
    (root/'z').mkdir();namespace=root/'z'/'.msae_keys'
    if kind=='directory':namespace.mkdir();marker=namespace/'synthetic-marker';marker.write_bytes(b'not a credential')
    elif kind=='file':namespace.write_bytes(b'not a credential');marker=namespace
    else:namespace.symlink_to(root/'a-before.txt');marker=namespace
    monkeypatch.setattr(n,'ROOT',root)
    original=os.open;observations=[]
    def checked(path,*args,**kwargs):
        observations.append(str(path))
        assert str(path) not in {'.msae_keys','synthetic-marker'},'credential namespace opened'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(os,'open',checked)
    before=set(os.listdir('/proc/self/fd'))
    with pytest.raises(n.GateFailure,match='history_credential_namespace_prohibited'):
        list(n._history_objects()) if walker=='history' else n._descriptor_tree(root)
    assert marker.exists() and set(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('error',[OSError,KeyboardInterrupt])
def test_history_admission_monitor_close_failure_blocks_and_releases_tree(tmp_path,monkeypatch,error):
    root=tmp_path/'synthetic-monitor-fault';root.mkdir();(root/'ordinary.txt').write_bytes(b'synthetic')
    monkeypatch.setattr(n,'ROOT',root)
    monitor=os.stat('/proc/self/fd');original=os.close;fired=[]
    def close(fd):
        info=os.fstat(fd);original(fd)
        if (info.st_dev,info.st_ino)==(monitor.st_dev,monitor.st_ino):
            fired.append(fd);raise error('synthetic admission-monitor close fault')
    monkeypatch.setattr(os,'close',close)
    before=set(os.listdir('/proc/self/fd'))
    with pytest.raises(error):list(n._history_objects())
    assert fired and (root/'ordinary.txt').exists() and set(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('walker',['history','inventory'])
def test_census_root_credential_ancestry_is_rejected_before_open(tmp_path,monkeypatch,walker):
    root=tmp_path/'.msae_keys'/'synthetic-child';root.mkdir(parents=True)
    monkeypatch.setattr(n,'ROOT',root)
    def forbidden(*args,**kwargs):raise AssertionError('credential ancestry opened')
    monkeypatch.setattr(os,'open',forbidden)
    with pytest.raises(n.GateFailure,match='history_credential_namespace_prohibited'):
        list(n._history_objects()) if walker=='history' else n._descriptor_tree(root)


@pytest.mark.parametrize('group',['public','raw'])
@pytest.mark.parametrize('attack',['bytes','third_alias','stage_substitution','ancestor_mode'])
def test_last_private_digest_cannot_bless_earlier_controller_group(tmp_path,monkeypatch,group,attack):
    # This isolates aggregate custody, not history/scientific eligibility.
    f=Fixture(tmp_path,monkeypatch)
    n.PROV.mkdir(parents=True,mode=0o755);n.PROV.chmod(0o755)
    f.session.register('baseline.json',j.create_pair(n.PROV/'baseline.json',b'{}\n',mode=0o644))
    n.DATA.mkdir(parents=True,mode=0o700);n.DATA.chmod(0o700)
    (n.DATA/'raw').mkdir(mode=0o700)
    f.session.raw_manifest=r.publish_flat_pairs(n.RAW,{name:b'aaaa' for name in [*n.SOURCE_FILES.values(),n.LICENSE_FILE]},directory_mode=0o555,file_mode=0o444)
    f.session.private_manifest=r.publish_role_pairs(n.PRIVATE,{role:b'opaque synthetic private bytes' for role in r.ROLES})
    f.session.checkpoint()
    first=n.PROV/'baseline.json' if group=='public' else n.RAW/n.LICENSE_FILE
    original_validate=j.OwnedPair.validate;original_read=os.pread;armed=[];fired=[]
    def validate(pair,*,durable=False):
        if durable and os.readlink('/proc/self/fd/'+str(pair.fd)).startswith(str(n.PRIVATE/'c2')+'/'):armed.append(True)
        return original_validate(pair,durable=durable)
    def read(fd,*args):
        value=original_read(fd,*args)
        if armed and not fired:
            fired.append(True)
            if attack=='bytes':
                old=first.stat();first.chmod(0o600);first.write_bytes(b'xxx' if group=='public' else b'bbbb');first.chmod(old.st_mode & 0o777);os.utime(first,ns=(old.st_atime_ns,old.st_mtime_ns))
            elif attack=='third_alias':os.link(first,f.external/'retained-third-alias')
            elif attack=='stage_substitution':
                stage=first.with_name('.'+first.name+'.stage');stage.rename(stage.with_name('retained-original-stage'));stage.write_bytes(b'foreign')
            else:first.parent.chmod(0o700)
        return value
    monkeypatch.setattr(j.OwnedPair,'validate',validate);monkeypatch.setattr(os,'pread',read)
    before=set(os.listdir('/proc/self/fd'))
    with pytest.raises((r.RuntimeBlocked,j.PairFailure)):
        with n.paired_control_session(f.session):f.controller.validate_current_custody(durable=True)
    assert fired==[True] and first.exists() and set(os.listdir('/proc/self/fd'))==before


def test_last_signed_subject_cannot_bless_earlier_subject_drift(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);first=f.root/'TODO.md';fired=[];original=c._CatalogReader.validate
    def validate(reader,**kwargs):
        result=original(reader,**kwargs)
        if reader.path.name=='prepare_msae_independent_source_v10.py' and not fired:
            old=first.stat();raw=first.read_bytes();first.write_bytes(b'X'+raw[1:]);os.utime(first,ns=(old.st_atime_ns,old.st_mtime_ns));fired.append(True)
        return result
    monkeypatch.setattr(c._CatalogReader,'validate',validate)
    before=set(os.listdir('/proc/self/fd'))
    with pytest.raises((r.RuntimeBlocked,j.PairFailure)):f.approvals.verify_release()
    assert fired and first.exists() and set(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('edge',['pair','review'])
def test_actual_signed_authority_pressure_admits_each_constructor(tmp_path,monkeypatch,edge):
    f=Fixture(tmp_path,monkeypatch);f.authority()
    baseline=set(os.listdir('/proc/self/fd'));realopen=os.open;realclose=os.close
    original_release=f.approvals.verify_release;original_close=j.OwnedPair.close
    fillers=[];peaks=[];filled=[]
    authority_inode=os.stat(n.PROV/'authority.json').st_ino
    def fill():
        target=4085 if edge=='pair' else 4086
        for _ in range(target-r._current_fd_count()):fillers.append(realopen('/dev/null',os.O_RDONLY))
        assert r._current_fd_count()==target;filled.append(edge)
    def release():
        result=original_release()
        if edge=='pair':fill()
        return result
    def close(pair,**kwargs):
        is_authority=not pair.closed and os.fstat(pair.fd).st_ino==authority_inode
        result=original_close(pair,**kwargs)
        if is_authority and edge=='review':fill()
        return result
    def opening(*args,**kwargs):
        fd=realopen(*args,**kwargs)
        if filled:peaks.append(len(os.listdir('/proc/self/fd'))-1)
        return fd
    monkeypatch.setattr(f.approvals,'verify_release',release)
    monkeypatch.setattr(j.OwnedPair,'close',close);monkeypatch.setattr(os,'open',opening)
    try:
        with pytest.raises(r.RuntimeBlocked,match='observation_fd_admission'):
            f.approvals.verify_authority(f.session)
    finally:
        for fd in fillers:realclose(fd)
        (tmp_path/'observed-pressure.json').write_text(__import__('json').dumps({'edge':edge,'filled':filled,'max_actual_open_peak':max(peaks) if peaks else None,'observer_descriptor_subtracted':1,'baseline_restored':set(os.listdir('/proc/self/fd'))==baseline})+'\n')
    assert filled==[edge] and peaks and max(peaks)<=4096
    assert set(os.listdir('/proc/self/fd'))==baseline and (n.PROV/'authority.json').stat().st_nlink==2


def test_actual_acquire_review_reread_pressure_stops_before_initiation(tmp_path,monkeypatch):
    import acquire_msae_independent_norspan_v1 as acquisition
    f=Fixture(tmp_path,monkeypatch);f.authority()
    baseline=set(os.listdir('/proc/self/fd'));realopen=os.open;realclose=os.close
    original=f.approvals.verify_authority;fillers=[];peaks=[];filled=[];entry_calls=[]
    def authority(session):
        review=original(session)
        for _ in range(4086-r._current_fd_count()):fillers.append(realopen('/dev/null',os.O_RDONLY))
        assert r._current_fd_count()==4086;filled.append(True)
        return review
    def opening(*args,**kwargs):
        fd=realopen(*args,**kwargs)
        if filled:peaks.append(len(os.listdir('/proc/self/fd'))-1)
        return fd
    def forbidden(*args,**kwargs):
        entry_calls.append(True);raise AssertionError('unadmitted reread reached acquisition entry')
    monkeypatch.setattr(f.approvals,'verify_authority',authority);monkeypatch.setattr(os,'open',opening)
    monkeypatch.setattr(acquisition,'acquire',forbidden)
    try:
        with pytest.raises(r.RuntimeBlocked,match='observation_fd_admission'):f.controller.execute('acquire')
    finally:
        for fd in fillers:realclose(fd)
        (tmp_path/'observed-pressure.json').write_text(__import__('json').dumps({'filled':filled,'acquisition_entry_calls':entry_calls,'max_actual_open_peak':max(peaks) if peaks else None,'observer_descriptor_subtracted':1,'baseline_restored':set(os.listdir('/proc/self/fd'))==baseline})+'\n')
    assert filled==[True] and not entry_calls and peaks and max(peaks)<=4096
    assert set(os.listdir('/proc/self/fd'))==baseline and not (n.PROV/'network_started.json').exists()


@pytest.mark.parametrize('transport',['approval_key','release_approval','release_signature','authority_approval','authority_signature'])
def test_actual_approval_transport_pressure_admits_each_input_after_guard(tmp_path,monkeypatch,transport):
    from types import SimpleNamespace
    f=Fixture(tmp_path,monkeypatch);f.authority()
    source_raw,source_sig,_=f.approvals._authority
    inputs={'approval_key':f.key,'release_approval':f.approvals.release,'release_signature':f.approvals.release_signature,
            'authority_approval':source_raw,'authority_signature':source_sig}
    paths={}
    for name,raw in inputs.items():
        path=f.external/('transport-'+name);path.write_bytes(raw);path.chmod(0o644);paths[name]=str(path)
    args=SimpleNamespace(**paths,approval_key_sha256=f.approvals.key_sha256,release_sha256=f.approvals.release_sha256,
        authority_approval_sha256=f.approvals._authority[2],outside_catalog=str(f.store.path),catalog_sha256=f.store.sha256,lineage_sha256=f.session.lineage)
    baseline=set(os.listdir('/proc/self/fd'));realopen=os.open;realclose=os.close;original=c._placement
    fillers=[];peaks=[];filled=[];subjects=[]
    def placement(path,*args,**kwargs):
        result=original(path,*args,**kwargs)
        if path==Path(paths[transport]):
            for _ in range(4090-r._current_fd_count()):fillers.append(realopen('/dev/null',os.O_RDONLY))
            assert r._current_fd_count()==4090;filled.append(transport)
        return result
    def opening(path,*args,**kwargs):
        fd=realopen(path,*args,**kwargs)
        if filled:
            peaks.append(len(os.listdir('/proc/self/fd'))-1)
            if str(path)!='/proc/self/fd':subjects.append(str(path))
        return fd
    monkeypatch.setattr(c,'_placement',placement);monkeypatch.setattr(os,'open',opening)
    try:
        with pytest.raises(r.RuntimeBlocked,match='observation_fd_admission'):c.from_arguments(args)
    finally:
        for fd in fillers:realclose(fd)
        (tmp_path/'observed-pressure.json').write_text(__import__('json').dumps({'transport':transport,'filled':filled,'unsafe_subject_opens':subjects,'max_actual_open_peak':max(peaks) if peaks else None,'observer_descriptor_subtracted':1,'baseline_restored':set(os.listdir('/proc/self/fd'))==baseline})+'\n')
    assert filled==[transport] and not subjects and peaks and max(peaks)<=4096
    assert set(os.listdir('/proc/self/fd'))==baseline


def test_production_transport_guard_stops_before_any_input_observation(monkeypatch):
    from types import SimpleNamespace
    assert 'synthetic-project' not in str(n.ROOT)
    def forbidden(*args,**kwargs):raise AssertionError('production guard allowed input observation')
    monkeypatch.setattr(r,'read_ordinary_file',forbidden);monkeypatch.setattr(c,'_placement',forbidden)
    with pytest.raises(n.GateFailure,match='jpc_whole_qualification_pending'):c.from_arguments(SimpleNamespace())
