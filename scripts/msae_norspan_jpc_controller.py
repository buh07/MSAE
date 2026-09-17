"""Explicit immutable outside-catalog transport and actual command integration.

Never discovers latest, adopts files, repairs evidence, retries started work or
removes the production guard. Catalog digests authenticate custody expectations,
not owner approval; approvals are a separate signed outside trust-root channel.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import re
import stat
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r
import msae_norspan_jpc_controls as controls

MAX_SNAPSHOTS = 64
MAX_CATALOG_BYTES = 4 * 1024**2


class _CatalogReader:
    """Ordinary nlink1 files, owned until the entire catalog chain is fenced."""
    def __init__(self,path,expected_sha256,*,mode=0o644,expected_count=None):
        self.path,self.sha256 = path,expected_sha256
        self.parent,self.fd,self.closed = None,None,False
        try:
            r._sha_literal(expected_sha256,'ordinary_expected_bytes')
            if type(mode) is not int or not 0<=mode<=0o777 or expected_count is not None and (type(expected_count) is not int or not 0<=expected_count<=MAX_CATALOG_BYTES):
                raise r.RuntimeBlocked('ordinary_expected_schema')
            r.admit_observation_fds(path)
            self.parent = j._open_parent_fd(path)
            self.fd = os.open(path.name,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,dir_fd=self.parent)
            before = os.fstat(self.fd)
            if (not stat.S_ISREG(before.st_mode) or stat.S_IMODE(before.st_mode)!=mode
                    or before.st_nlink!=1 or before.st_size>MAX_CATALOG_BYTES):
                raise r.RuntimeBlocked('catalog_ordinary_custody')
            self.fp = j._fingerprint(before)
            self.count = before.st_size
            if expected_count is not None and self.count!=expected_count:
                raise r.RuntimeBlocked('ordinary_expected_count')
            self.validate()
        except BaseException as exc:
            self.close(primary=exc)
            raise

    def fence(self):
        if self.closed:
            raise r.RuntimeBlocked('catalog_reader_closed')
        if (j._fingerprint(os.fstat(self.fd))!=self.fp
                or j._fingerprint(os.stat(self.path.name,dir_fd=self.parent,follow_symlinks=False))!=self.fp):
            raise r.RuntimeBlocked('catalog_original_drift')
        j._validate_parent_fd(self.parent)

    def read(self,*,copy=True):
        self.fence()
        os.lseek(self.fd,0,os.SEEK_SET)
        chunks=[];count=0;digest=hashlib.sha256()
        while block:=os.read(self.fd,min(1024**2,self.count-count+1)):
            count+=len(block)
            if count>self.count:
                raise r.RuntimeBlocked('catalog_original_growth')
            digest.update(block)
            if copy:chunks.append(block)
        if count!=self.count or digest.hexdigest()!=self.sha256:
            raise r.RuntimeBlocked('catalog_expected_bytes_drift')
        self.fence()
        return b''.join(chunks) if copy else None

    def validate(self,*,durable=False):
        self.read(copy=False)
        if durable:
            os.fsync(self.fd);os.fsync(self.parent)
            self.read(copy=False)

    def close(self,*,primary=None):
        if not self.closed:
            self.closed=True
            if self.parent is None:
                j._close_fds([] if self.fd is None else [self.fd],primary=primary)
            else:
                j._finish(self.parent,self.fd,primary)


def _placement(path, project_root):
    j._names(path)
    j._names(project_root / 'sentinel')
    if not str(path).startswith('/jumbo/') or path == project_root or project_root in path.parents:
        raise r.RuntimeBlocked('outside_catalog_placement')


def _write_snapshot(path: Path, raw: bytes, expected_names: set[str]) -> None:
    if type(raw) is not bytes or len(raw) > MAX_CATALOG_BYTES:
        raise r.RuntimeBlocked('catalog_size')
    resources = []
    fd = None
    primary = None
    try:
        r.admit_observation_fds(path.parent)
        parent = r._directory(path.parent,reserve=False,mode=0o700)
        resources.append(parent)
        parent.validate(expected_names)
        r.admit_observation_fds(path)
        fd = os.open(path.name,os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK,0o600,dir_fd=parent.fd)
        before = os.fstat(fd)
        view = memoryview(raw)
        while view:
            count = os.write(fd,view)
            if count <= 0:
                raise r.RuntimeBlocked('catalog_short_write')
            view = view[count:]
        os.fchmod(fd,0o644)
        os.fsync(fd)
        current = os.fstat(fd)
        if (current.st_dev != before.st_dev or current.st_ino != before.st_ino
                or current.st_nlink != 1 or current.st_size != len(raw)
                or j._fingerprint(os.stat(path.name,dir_fd=parent.fd,follow_symlinks=False)) != j._fingerprint(current)):
            raise r.RuntimeBlocked('catalog_publication_drift')
        parent.validate(expected_names | {path.name})
        parent.validate(expected_names | {path.name},durable=True)
        # Keep original writer and ALL ancestors through the final copied read.
        # Foreign objects introduced by that reader must not advance the catalog.
        r.admit_observation_fds(path)
        if r.read_ordinary_file(path,max_bytes=MAX_CATALOG_BYTES) != raw:
            raise r.RuntimeBlocked('catalog_final_read_drift')
        digest=hashlib.sha256();offset=0
        while block:=os.pread(fd,min(1024**2,len(raw)-offset+1),offset):
            offset+=len(block)
            if offset>len(raw):raise r.RuntimeBlocked('catalog_writer_growth')
            digest.update(block)
        if offset!=len(raw) or digest.hexdigest()!=hashlib.sha256(raw).hexdigest():
            raise r.RuntimeBlocked('catalog_writer_bytes_drift')
        parent.validate(expected_names | {path.name})
        if (j._fingerprint(os.fstat(fd))!=j._fingerprint(current)
                or j._fingerprint(os.stat(path.name,dir_fd=parent.fd,follow_symlinks=False))!=j._fingerprint(current)):
            raise r.RuntimeBlocked('catalog_final_writer_drift')
    except BaseException as exc:
        primary = exc
        raise
    finally:
        first = primary
        try:
            j._close_fds([] if fd is None else [fd],primary=first)
        except BaseException as exc:
            first = exc
        r._close_resources(resources,primary=first)
        if primary is None and first is not None:
            raise first


class CatalogStore:
    def __init__(self, root, project_root):
        self.root, self.project_root = root, project_root
        self.sequence = -1
        self.path = None
        self.sha256 = None
        self._poisoned = False

    @staticmethod
    def _name(sequence):
        return f'catalog-{sequence:06d}.json'

    def checkpoint(self, session):
        if self._poisoned or self.sequence + 1 >= MAX_SNAPSHOTS:
            raise r.RuntimeBlocked('catalog_store_poisoned_or_limit')
        sequence = self.sequence + 1
        value = {'schema_version':'norspan_catalog_snapshot_v1','sequence':sequence,
                 'previous_sha256':self.sha256,'catalog':session.catalog(transport=True)}
        raw = r.canonical_bytes(value) + b'\n'
        path = self.root / self._name(sequence)
        try:
            _write_snapshot(path,raw,{self._name(i) for i in range(sequence)})
        except BaseException:
            self._poisoned = True
            raise
        self.sequence, self.path, self.sha256 = sequence,path,hashlib.sha256(raw).hexdigest()

    @classmethod
    def create(cls, path, root, *, project_root, lineage_sha256):
        _placement(path / 'sentinel',project_root)
        r.admit_observation_fds(path)
        with r._directory(path,reserve=True,mode=0o700) as directory:
            directory.validate(set(),durable=True)
        session = controls.ControlSession(root,lineage_sha256=lineage_sha256)
        result = cls(path,project_root)
        session._checkpoint = result.checkpoint
        session.checkpoint()
        return session,result

    @classmethod
    def load(cls, path, *, expected_sha256, root, project_root, lineage_sha256):
        _placement(path,project_root)
        r._sha_literal(expected_sha256,'outside_catalog_snapshot')
        match = re.fullmatch(r'catalog-([0-9]{6})\.json',path.name)
        if match is None or int(match[1]) >= MAX_SNAPSHOTS:
            raise r.RuntimeBlocked('catalog_snapshot_name')
        sequence = int(match[1])
        result = cls(path.parent,project_root)
        resources=[];readers=[];primary=None
        try:
            r.admit_observation_fds(path.parent)
            directory=r._directory(path.parent,reserve=False,mode=0o700)
            resources.append(directory)
            directory.validate({result._name(i) for i in range(sequence+1)})
            pin = expected_sha256
            final = None
            for i in reversed(range(sequence+1)):
                reader=_CatalogReader(path.parent/result._name(i),pin)
                resources.append(reader);readers.append(reader)
                raw=reader.read()
                value = r._json(raw)
                if (hashlib.sha256(raw).hexdigest() != pin or type(value) is not dict
                        or raw != r.canonical_bytes(value)+b'\n'
                        or set(value) != {'schema_version','sequence','previous_sha256','catalog'}
                        or value['schema_version'] != 'norspan_catalog_snapshot_v1'
                        or type(value['sequence']) is not int or value['sequence'] != i):
                    raise r.RuntimeBlocked('catalog_snapshot_binding')
                catalog = value['catalog']
                loaded = controls.ControlSession.from_catalog(root,catalog,
                    expected_sha256=hashlib.sha256(r.canonical_bytes(catalog)).hexdigest(),lineage_sha256=lineage_sha256)
                if final is None: final = loaded
                if i:
                    r._sha_literal(value['previous_sha256'],'catalog_predecessor')
                elif value['previous_sha256'] is not None:
                    raise r.RuntimeBlocked('catalog_genesis_predecessor')
                pin = value['previous_sha256']
            for reader in readers:reader.validate(durable=True)
            directory.validate({result._name(i) for i in range(sequence+1)},durable=True)
            for reader in readers:reader.validate()
            # ALL earlier originals/named aliases after the final byte scan.
            for reader in readers:reader.fence()
            directory.validate({result._name(i) for i in range(sequence+1)})
        except BaseException as exc:
            primary=exc
            raise
        finally:
            r._close_resources(resources,primary=primary)
        result.sequence,result.path,result.sha256 = sequence,path,expected_sha256
        final._checkpoint = result.checkpoint
        return final,result


class Controller:
    def __init__(self, session, catalog, approvals):
        import prepare_msae_independent_norspan_v1 as p
        if session.root != p.PROV or approvals.root != p.ROOT:
            raise r.RuntimeBlocked('controller_root')
        self.session,self.catalog,self.approvals = session,catalog,approvals
        session.authority = approvals
        self._failed = False

    def execute(self, command, args=None):
        import prepare_msae_independent_norspan_v1 as p
        # Always BEFORE approval/catalog/state inspection. No synthetic CLI bypass.
        p.require_jpc_qualification()
        if self._failed:
            raise r.RuntimeBlocked('controller_invocation_failed')
        table = {'build-history':p.cmd_build_history,'build-authority':p.cmd_build_authority,
                 'prepare':p.cmd_prepare,'verify':p.cmd_verify,'recover':self.recover}
        try:
            with p.paired_control_session(self.session):
                self.approvals.verify_release()
                if command == 'acquire':
                    import acquire_msae_independent_norspan_v1 as a
                    review = self.approvals.verify_authority(self.session)
                    r.admit_observation_fds(review)
                    result = a.acquire(hashlib.sha256(r.read_ordinary_file(review)).hexdigest())
                else:
                    if command not in table:
                        raise r.RuntimeBlocked('controller_command')
                    result = table[command](args)
                self.validate_current_custody(durable=True)
                return result
        except BaseException:
            self._failed = True
            raise

    def validate_current_custody(self, *, durable):
        """Hold ALL public/raw/private originals across final aggregate fences.

        Separate group verification cannot cover a last private digest changing
        an earlier public/raw object. Expectations remain outside; private bytes
        are hashed opaquely, never parsed or exposed as scoring payloads.
        """
        import prepare_msae_independent_norspan_v1 as p
        inv = self.session.inventory()
        if inv['partial']:
            raise r.RuntimeBlocked('partial_controller_custody')
        public = set(inv['logical'])
        raw = self.session.raw_manifest
        private = self.session.private_manifest
        fields = {'sha256','bytes','mode','nlink','pair'}
        if 'source_acquisition.json' in public:
            raw = {name:{key:item[key] for key in fields}
                   for name,item in self.session.canonical('source_acquisition.json')['files'].items()}
        containing = 'seal.json' if 'seal.json' in public else 'source_ready.json' if 'source_ready.json' in public else None
        if containing:
            private = {role:{key:item[key] for key in fields}
                       for role,item in self.session.canonical(containing)['payloads'].items()}
        if raw is not None and set(raw) != {*p.SOURCE_FILES.values(),p.LICENSE_FILE}:
            raise r.RuntimeBlocked('controller_raw_set')
        if private is not None and set(private) != set(r.ROLES):
            raise r.RuntimeBlocked('controller_role_set')
        resources,pairs,directories = [],[],[]
        primary = None
        def directory(path,mode,names):
            r.admit_observation_fds(path)
            owned = r._directory(path,reserve=False,mode=mode)
            resources.append(owned);directories.append((owned,names))
            owned.validate(names)
        def pair(path,receipt):
            if sum(x.receipt.byte_count for x in pairs)+receipt.byte_count > r.TOTAL_BYTES_LIMIT:
                raise r.RuntimeBlocked('controller_aggregate_byte_budget')
            r.admit_observation_fds(path)
            owned = j.open_owned_pair(path,receipt)
            resources.append(owned);pairs.append(owned)
        try:
            directory(p.PROV,0o755,set(inv['physical']))
            for name in sorted(public):pair(p.PROV/name,self.session.expected(name))
            if raw is not None or private is not None:
                directory(p.DATA,0o700,({'raw'} if raw is not None else set()) | ({'private'} if private is not None else set()))
            else:
                try:p.DATA.lstat()
                except FileNotFoundError:pass
                else:raise r.RuntimeBlocked('unmanifested_controller_data')
            if raw is not None:
                directory(p.DATA/'raw',0o700,{p.COMMIT})
                directory(p.RAW,0o555,r._pair_names(raw))
                for name,item in raw.items():pair(p.RAW/name,r._expected_receipt(p.RAW/name,item,0o444))
            if private is not None:
                directory(p.PRIVATE,0o700,{role.lower() for role in r.ROLES})
                for role in r.ROLES:
                    path=p.PRIVATE/role.lower()
                    directory(path,0o700,{'payload.jsonl','.payload.jsonl.stage'})
                    pair(path/'payload.jsonl',r._expected_receipt(path/'payload.jsonl',private[role],0o600))
            identities={(x.receipt.device,x.receipt.inode) for x in pairs}
            if len(identities)!=len(pairs):
                raise r.RuntimeBlocked('controller_cross_object_inode')
            r._validate_all_pairs(pairs,durable=durable)
            for owned,names in directories:owned.validate(names,durable=durable)
            r._validate_all_pairs(pairs,durable=False)
            for owned,names in directories:owned.validate(names)
        except BaseException as exc:
            primary=exc
            raise
        finally:
            r._close_resources(resources,primary=primary)

    def recover(self, args=None):
        import prepare_msae_independent_norspan_v1 as p
        p.require_jpc_qualification()
        counts = {'local_status_observation_attempts':0,'local_status_observation_completed':0,
                  'terminal_raw_reconstruction_attempts':0}
        token = p._RECOVERY_COUNTS.set(counts)
        try:
            with p.paired_control_session(self.session):
                self.approvals.verify_release()
                inv = self.session.inventory()
                names = set(inv['logical'])
                terminal = bool(names & {'seal.json','rejection.json'})
                physical = set(inv['physical'])
                raw_started = bool(physical & {'raw_access_started.json','.raw_access_started.json.stage'})
                network_started = bool(physical & {'network_started.json','.network_started.json.stage'})
                if raw_started and not terminal or network_started and not names & {'source_acquisition.json','rejection.json'}:
                    raise r.RuntimeBlocked('started_without_terminal_no_retry')
                if inv['partial']:
                    raise r.RuntimeBlocked('partial_control_evidence_unresolved')
                state = p.classify_protocol_state()
                if state == 'clean_reviewed':
                    raise r.RuntimeBlocked('recovery_no_typed_baseline')
                cfg,baseline,registry = p.validate_baseline_chain()
                if state != 'baseline':
                    p.validate_authority_chain()
                scratch = None
                if 'acquisition_entry.json' in names:
                    entry = self.session.canonical('acquisition_entry.json',keys=p.CONTROL_FIELDS['acquisition_entry.json'])
                    with r.reopen_scratch(entry['scratch_binding']) as lease:
                        if not network_started: lease.validate_pristine()
                        scratch = lease.snapshot(durable=True)
                    containing = 'source_acquisition.json' if 'source_acquisition.json' in names else 'rejection.json' if 'rejection.json' in names and not raw_started else None
                    if containing:
                        original = self.session.canonical(containing)['scratch']
                        p.validate_scratch_record(original)
                        if r.canonical_bytes(original) != r.canonical_bytes(scratch):
                            raise r.RuntimeBlocked('retained_scratch_current_summary_drift')
                verification = None
                if state in {'acquisition_terminal','scientific_terminal'}:
                    verification = p.cmd_verify(None)
                elif state in {'scientific_entered','raw_ready'}:
                    p.validate_control_chain()
                elif state not in {'baseline','authority','acquisition_entered','network_ready'}:
                    raise r.RuntimeBlocked('recovery_state_not_permitted')
                # Current fsync + full byte/ancestor/cardinality fences; never
                # infer a past failed producer returned successfully.
                self.validate_current_custody(durable=True)
                p.validate_history_registry(registry,cfg)
                current = p.evidence_snapshot()
                p.validate_evidence(current);p.evidence_compatible(baseline['evidence'],current)
                if p.classify_protocol_state() != state:
                    raise r.RuntimeBlocked('recovery_final_state_drift')
                return {'status':'verified_current_observation_not_launch_authority',
                        'state':state,'verification':verification,'history_replayed':True,
                        'approval_verified':True,
                        'approval_authentication_method':getattr(self.approvals,'authentication_method','UNKNOWN'),
                        'signed_approval_verified':getattr(self.approvals,'authentication_method','UNKNOWN') == 'ed25519_detached',
                        'production_canonical_authority_established':False,
                        'scratch_current_summary':scratch, 'historical_scratch_bytes_attested':False,
                        'historical_success_inferred':False,'source_work_authorized':False,
                        'source_acquisition_commands':0,'source_network_operations':0,'model_operations':0,
                        'operation_scope':'controller_direct_calls_only_not_status_helpers',
                        'status_helper_effects':'UNVERIFIED',
                        'status_protected_content_exclusion':'UNVERIFIED',
                        'status_network_isolation':'UNVERIFIED',
                        'C2_scientific_opens':0,**counts}
        finally:
            p._RECOVERY_COUNTS.reset(token)


def add_arguments(parser, *, genesis=False):
    """Explicit outside pins; no enroll/discover/production-override switches."""
    parser.add_argument('--approval-kind',choices=['owner-markdown','ed25519'],default='owner-markdown')
    for name in ['release-approval','release-sha256','lineage-sha256']:
        parser.add_argument('--'+name,required=True)
    for name in ['approval-key','approval-key-sha256','release-signature']:
        parser.add_argument('--'+name)
    if genesis:
        parser.add_argument('--catalog-directory',required=True)
    else:
        parser.add_argument('--outside-catalog',required=True)
        parser.add_argument('--catalog-sha256',required=True)
    for name in ['authority-approval','authority-signature','authority-approval-sha256']:
        parser.add_argument('--'+name)


def from_arguments(args, *, genesis=False):
    import prepare_msae_independent_norspan_v1 as p
    import msae_norspan_jpc_authority as authority
    p.require_jpc_qualification()  # BEFORE even key/catalog observations.
    def read(name, limit):
        path = Path(getattr(args,name))
        _placement(path,p.ROOT)
        r.admit_observation_fds(path)
        return r.read_ordinary_file(path,max_bytes=limit)
    # Legacy programmatic namespaces retain signed behavior; new CLI defaults owner.
    kind = getattr(args,'approval_kind','ed25519')
    if kind == 'owner-markdown':
        if any(getattr(args,name,None) is not None for name in
               ['approval_key','approval_key_sha256','release_signature','authority_signature']):
            raise r.RuntimeBlocked('owner_approval_mixed_signature_arguments')
        from msae_norspan_owner_approval import OwnerApprovals
        approvals = OwnerApprovals(p.ROOT,release=read('release_approval',MAX_CATALOG_BYTES),
                                  release_sha256=args.release_sha256)
        authority_fields = [args.authority_approval,args.authority_approval_sha256]
        if any(authority_fields):
            if not all(authority_fields):
                raise r.RuntimeBlocked('authority_approval_arguments')
            approvals.bind_authority(read('authority_approval',MAX_CATALOG_BYTES),None,
                                     expected_sha256=args.authority_approval_sha256)
    elif kind == 'ed25519':
        if not all(getattr(args,name,None) for name in ['approval_key','approval_key_sha256','release_signature']):
            raise r.RuntimeBlocked('approval_signature_arguments')
        approvals = authority.Approvals(p.ROOT,key=read('approval_key',44),
            key_sha256=args.approval_key_sha256,release=read('release_approval',MAX_CATALOG_BYTES),
            release_signature=read('release_signature',64),release_sha256=args.release_sha256)
        authority_fields = [args.authority_approval,args.authority_signature,args.authority_approval_sha256]
        if any(authority_fields):
            if not all(authority_fields):
                raise r.RuntimeBlocked('authority_approval_arguments')
            approvals.bind_authority(read('authority_approval',MAX_CATALOG_BYTES),read('authority_signature',64),
                                     expected_sha256=args.authority_approval_sha256)
    else:
        raise r.RuntimeBlocked('approval_kind')
    if genesis:
        session,store = CatalogStore.create(Path(args.catalog_directory),p.PROV,
                                            project_root=p.ROOT,lineage_sha256=args.lineage_sha256)
    else:
        session,store = CatalogStore.load(Path(args.outside_catalog),expected_sha256=args.catalog_sha256,
            root=p.PROV,project_root=p.ROOT,lineage_sha256=args.lineage_sha256)
    return Controller(session,store,approvals)
