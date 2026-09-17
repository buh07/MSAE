"""Finite outside-expected paired controls; integration, never launch approval.

A catalog hash authenticates bytes only against the caller's prior expectation.
It is NOT independent/canonical approval. Production guard remains unconditional;
this class and its synthetic tests grant zero scientific/source/model capability.
Live registration accepts actual successful producer receipts, never discovered
metadata. Fresh invocations need an outside pinned catalog and separate approval.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import stat
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r

class ControlSession:
    source_work_authorized = False

    def __init__(self, root: Path, *, lineage_sha256: str):
        j._names(root / 'sentinel')
        r._sha_literal(lineage_sha256, 'control_lineage')
        self.root, self.lineage = root, lineage_sha256
        self._receipts = {}
        self.raw_manifest = None
        self.private_manifest = None
        self.authority = None
        self._checkpoint = None
        self._poisoned = False

    def checkpoint(self) -> None:
        if self._poisoned:
            raise r.RuntimeBlocked('control_session_poisoned')
        if self._checkpoint is not None:
            try:
                self._checkpoint(self)
            except BaseException:
                self._poisoned = True
                raise

    def register(self, name: str, receipt: j.PairReceipt) -> None:
        if self._poisoned:
            raise r.RuntimeBlocked('control_session_poisoned')
        if name not in r.CONTROL_NAMES or name in self._receipts:
            raise r.RuntimeBlocked('control_registration_name_or_repeat')
        expected = j.receipt_from_record(self.root / name, j.receipt_record(receipt))
        if expected.mode != 0o644:
            raise r.RuntimeBlocked('control_receipt_mode')
        # Success receipt alone is not containing authority. Check current pair
        # before recording; failed/partial publication never becomes an expectation.
        r.admit_observation_fds(self.root / name)
        with j.open_owned_pair(self.root / name, expected) as pair:
            pair.validate()
        self._receipts[name] = expected
        self.checkpoint()

    @classmethod
    def from_catalog(cls, root: Path, catalog: dict, *, expected_sha256: str,
                     lineage_sha256: str):
        r._sha_literal(expected_sha256, 'outside_control_catalog')
        version = catalog.get('schema_version') if type(catalog) is dict else None
        fields = {'schema_version','lineage_sha256','controls'}
        if version == 'norspan_jpc_custody_catalog_v2':
            fields |= {'raw_manifest','private_manifest'}
        if (type(catalog) is not dict or set(catalog) != fields
                or version not in {'norspan_jpc_custody_catalog_v1','norspan_jpc_custody_catalog_v2'}
                or catalog['lineage_sha256'] != lineage_sha256
                or hashlib.sha256(r.canonical_bytes(catalog)).hexdigest() != expected_sha256
                or type(catalog['controls']) is not dict
                or not set(catalog['controls']) <= r.CONTROL_NAMES):
            raise r.RuntimeBlocked('outside_control_catalog_binding')
        result = cls(root, lineage_sha256=lineage_sha256)
        for name, record in catalog['controls'].items():
            receipt = j.receipt_from_record(root / name, record)
            if receipt.mode != 0o644:
                raise r.RuntimeBlocked('control_receipt_mode')
            result._receipts[name] = receipt
        if version == 'norspan_jpc_custody_catalog_v2':
            result.raw_manifest = catalog['raw_manifest']
            result.private_manifest = catalog['private_manifest']
            result.validate_manifests()
        return result

    def catalog(self, *, transport=False) -> dict:
        if self._poisoned:
            raise r.RuntimeBlocked('control_session_poisoned')
        value = {'schema_version':'norspan_jpc_custody_catalog_v1',
                'lineage_sha256':self.lineage,
                'controls':{name:j.receipt_record(receipt) for name,receipt in self._receipts.items()}}
        if transport:
            self.validate_manifests()
            value.update(schema_version='norspan_jpc_custody_catalog_v2',
                         raw_manifest=self.raw_manifest,private_manifest=self.private_manifest)
        return value

    def validate_manifests(self) -> None:
        # Schema only here; actual containing controls and current paired custody
        # are reconstructed by the controller before granting any observation.
        if self.raw_manifest is not None:
            import prepare_msae_independent_norspan_v1 as p
            names = {*p.SOURCE_FILES.values(),p.LICENSE_FILE}
            if type(self.raw_manifest) is not dict or set(self.raw_manifest) != names:
                raise r.RuntimeBlocked('catalog_raw_manifest_schema')
            for name, item in self.raw_manifest.items():
                r._expected_receipt(p.RAW/name,item,0o444)
        if self.private_manifest is not None:
            import prepare_msae_independent_norspan_v1 as p
            if type(self.private_manifest) is not dict or set(self.private_manifest) != set(r.ROLES):
                raise r.RuntimeBlocked('catalog_private_manifest_schema')
            for role, item in self.private_manifest.items():
                r._expected_receipt(p.PRIVATE/role.lower()/'payload.jsonl',item,0o600)

    def expected(self, name: str) -> j.PairReceipt:
        if self._poisoned:
            raise r.RuntimeBlocked('control_session_poisoned')
        if name not in self._receipts:
            raise r.RuntimeBlocked('outside_expected_receipt_missing:' + name)
        return self._receipts[name]

    def read(self, name: str, *, max_bytes: int = r.FILE_BYTES_LIMIT) -> bytes:
        receipt = self.expected(name)
        if type(max_bytes) is not int or not 0 <= max_bytes <= r.FILE_BYTES_LIMIT or receipt.byte_count > max_bytes:
            raise r.RuntimeBlocked("control_read_budget")
        r.admit_observation_fds(self.root / name)
        with j.open_owned_pair(self.root / name, receipt) as pair:
            return pair.read_bytes(max_bytes=max_bytes)

    def digest(self, name: str) -> dict:
        receipt = self.expected(name)
        r.admit_observation_fds(self.root / name)
        with j.open_owned_pair(self.root / name, receipt) as pair:
            pair.validate()
        return {'sha256':receipt.sha256, 'bytes':receipt.byte_count,
                'mode':receipt.mode,'nlink':2,'pair':j.receipt_record(receipt)}

    def read_prefix(self, name: str, *, limit: int) -> bytes:
        if type(limit) is not int or not 1 <= limit <= r.FILE_BYTES_LIMIT:
            raise r.RuntimeBlocked('control_prefix_limit_schema')
        receipt = self.expected(name)
        r.admit_observation_fds(self.root / name)
        with j.open_owned_pair(self.root / name, receipt) as pair:
            return pair.read_prefix(limit=limit)

    def canonical(self, name: str, *, keys=None) -> dict:
        raw = self.read(name)
        value = r._json(raw)
        if (type(value) is not dict or raw != r.canonical_bytes(value) + b'\n'
                or keys is not None and set(value) != set(keys)):
            raise r.RuntimeBlocked('paired_control_canonical_schema:' + name)
        return value

    def inventory(self) -> dict:
        resources = []
        primary = None
        try:
            r.admit_observation_fds(self.root)
            root = r._directory(self.root, reserve=False, mode=0o755)
            resources.append(root)
            names = r.bounded_names(root.fd, len(r.CONTROL_NAMES) * 2)
            prescribed = r._pair_names(r.CONTROL_NAMES)
            if names - prescribed:
                raise r.RuntimeBlocked('control_unknown_physical_object')
            partial = []
            complete = []
            for name in sorted(r.CONTROL_NAMES):
                stage = '.' + name + '.stage'
                present = names & {stage,name}
                if not present:
                    continue
                if present != {stage,name}:
                    partial.append(name)
                    continue
                # Complete-looking unregistered pairs are not adopted.
                r.admit_observation_fds(self.root/name)
                pair = j.open_owned_pair(self.root/name,self.expected(name))
                resources.append(pair)
                complete.append(name)
            missing = set(self._receipts) - set(complete)
            if missing:
                raise r.RuntimeBlocked('expected_control_pair_missing')
            root.validate(names)
            r._validate_all_pairs([x for x in resources if isinstance(x,j.OwnedPair)],durable=False)
            initiated = bool(names & {'network_started.json','.network_started.json.stage',
                                     'raw_access_started.json','.raw_access_started.json.stage'})
            return {'status':'unresolved' if partial else 'complete_current_observation',
                    'logical':complete,'physical':sorted(names),'partial':partial,
                    'initiated_no_retry':initiated,'source_work_authorized':False}
        except BaseException as exc:
            primary = exc
            raise
        finally:
            r._close_resources(resources,primary=primary)

    def validate_durable(self) -> None:
        """Current durability only, with aggregate original-FD byte fences."""
        inv = self.inventory()
        if inv['partial']:
            raise r.RuntimeBlocked('partial_control_durability_unresolved')
        resources = []
        primary = None
        try:
            r.admit_observation_fds(self.root)
            root = r._directory(self.root,reserve=False,mode=0o755)
            resources.append(root)
            for name in inv['logical']:
                r.admit_observation_fds(self.root/name)
                resources.append(j.open_owned_pair(self.root/name,self.expected(name)))
            pairs = resources[1:]
            r._validate_all_pairs(pairs,durable=True)
            root.validate(set(inv['physical']),durable=True)
            r._validate_all_pairs(pairs,durable=False)
            root.validate(set(inv['physical']))
        except BaseException as exc:
            primary = exc
            raise
        finally:
            r._close_resources(resources,primary=primary)


def recover_application_metadata(session: ControlSession, *, expected_implementation_sha256: str,
                                 expected_authority_review_sha256: str) -> dict:
    """Explicit SOURCE-FREE typed phase/lineage observation, not full approval.

    Pinned hashes are expectations, not authenticated independent approval. This
    integrates paired reads and retained scratch observations but cannot satisfy
    canonical/history/scientific replay alone. It never opens source/raw/private
    payloads or resumes a producer. The production CLI separately stays guarded.
    """
    import prepare_msae_independent_norspan_v1 as p
    r._sha_literal(expected_implementation_sha256,'implementation_expectation')
    r._sha_literal(expected_authority_review_sha256,'authority_review_expectation')
    inv = session.inventory()
    names = set(inv['logical'])
    terminal = bool(names & {'rejection.json','source_acquisition.json','seal.json'})
    raw_started = bool(set(inv['physical']) & {'raw_access_started.json','.raw_access_started.json.stage'})
    if inv['initiated_no_retry'] and (not terminal or raw_started and not names & {'rejection.json','seal.json'}):
        raise r.RuntimeBlocked('started_without_terminal_no_retry')
    if inv['partial']:
        return {'status':'incomplete_unresolved','source_operations':0,'model_operations':0,
                'source_work_authorized':False,'historical_success_inferred':False}
    prefix = ['current_history_registry.json','baseline.json','authority.json',
              'acquisition_entry.json','pre_network_ready.json','network_started.json']
    present = [name for name in prefix if name in names]
    if present != prefix[:len(present)]:
        raise r.RuntimeBlocked('recovery_phase_prefix')
    if not present:
        raise r.RuntimeBlocked('recovery_no_typed_baseline')
    values = {}
    schema = {
        'baseline.json':'msae_independent_norspan_v1_baseline_v1',
        'authority.json':'msae_independent_norspan_v1_authority_v1',
        'acquisition_entry.json':'msae_independent_norspan_v1_acquisition_entry_jpc_v1',
        'pre_network_ready.json':'msae_independent_norspan_v1_pre_network_ready_jpc_v1',
        'network_started.json':'msae_independent_norspan_v1_network_started_jpc_v1'}
    keys = {name:set(fields) for name,fields in p.CONTROL_FIELDS.items()}
    keys['acquisition_entry.json'] |= {'scratch_binding','entry_lineage_sha256'}
    keys['pre_network_ready.json'] |= {'scratch_binding'}
    keys['network_started.json'] |= {'scratch_binding'}
    links = {'baseline.json':{'current_history_registry_sha256':'current_history_registry.json'},
             'authority.json':{'baseline_sha256':'baseline.json','current_history_registry_sha256':'current_history_registry.json'},
             'acquisition_entry.json':{'baseline_sha256':'baseline.json','history_registry_sha256':'current_history_registry.json','authority_sha256':'authority.json'},
             'pre_network_ready.json':{'acquisition_entry_sha256':'acquisition_entry.json'},
             'network_started.json':{'pre_network_ready_sha256':'pre_network_ready.json'}}
    for name in present:
        value = session.canonical(name,keys=keys.get(name))
        values[name] = value
        if name == 'current_history_registry.json':
            if value.get('schema_version') != 'msae_independent_norspan_v1_current_history_registry_v1':
                raise r.RuntimeBlocked('recovery_history_schema')
            continue
        p.require_literals(value,{'schema_version':schema[name]},'recovery_schema')
        for field,predecessor in links[name].items():
            p.require_literals(value,{field:session.expected(predecessor).sha256},'recovery_lineage')
        for field in ['model_operations','gpu_queries','training_runs']:
            if field in value:
                p.require_literals(value,{field:0},'recovery_operations')
        for field in ['evidence','pre_authority_evidence','pre_entry_evidence']:
            if field in value:p.validate_evidence(value[field])
    if 'baseline.json' in values:
        p.require_literals(values['baseline.json'],{'implementation_review_sha256':expected_implementation_sha256,
                          'status':'eligible','source_namespace_absent_at_registry_start':True},'recovery_baseline')
    if 'authority.json' in values:
        p.require_literals(values['authority.json'],{'source_repo':p.REPO,'source_commit':p.COMMIT,
                          'source_files':[*p.SOURCE_FILES.values(),p.LICENSE_FILE],
                          'status':'awaiting_independent_authority_review'},'recovery_authority')
    scratch = None
    if 'acquisition_entry.json' in values:
        entry = values['acquisition_entry.json']
        p.require_literals(entry,{'source_repo':p.REPO,'source_commit':p.COMMIT,
                          'source_files':[*p.SOURCE_FILES.values(),p.LICENSE_FILE],
                          'authority_review_sha256':expected_authority_review_sha256,
                          'entry_lineage_sha256':session.lineage,'status':'entered','subprocesses_started':0},'recovery_entry')
        binding = entry['scratch_binding']
        p.require_literals(binding,{'authority_sha256':session.expected('authority.json').sha256,
                                    'entry_lineage_sha256':session.lineage},'recovery_scratch_lineage')
        for name in ['pre_network_ready.json','network_started.json']:
            if name in values:
                p.require_literals(values[name],{'scratch_binding':binding,'status':'ready' if name.startswith('pre_') else 'started'},'recovery_marker')
        with r.reopen_scratch(binding) as lease:
            if not inv['initiated_no_retry']:lease.validate_pristine()
            scratch = lease.snapshot(durable=True)
    # Scientific/terminal metadata alone MUST NOT become terminal scientific
    # verification. Existing full history/science/whole-authority gates remain.
    return {'status':'terminal_metadata_observed_pending_full_validation' if terminal else 'prestart_metadata_observed_pending_full_validation',
            'controls':sorted(names),'scratch':scratch,'source_operations':0,'model_operations':0,
            'source_work_authorized':False,'historical_success_inferred':False,
            'canonical_authority':'NOT_ESTABLISHED','history_science_replay':'NOT_COMPLETED'}
