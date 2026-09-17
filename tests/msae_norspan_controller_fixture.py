"""Fresh synthetic full application fixtures. No actual gate outcome is mocked.

Extracted public source fixture producers from legacy tests; do not collect the
legacy suite. Only process/status/transport/storage-placement producers replaced.
"""
from pathlib import Path
import hashlib
import subprocess
import stat
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_msae_independent_norspan_v1 as n
import msae_norspan_jpc_runtime as r
import msae_norspan_jpc_controller as c
import msae_norspan_jpc_authority as approval

def _require_public_source_mode(path,mode):
    observed=path.lstat()
    assert stat.S_ISREG(observed.st_mode) and observed.st_nlink==1
    assert stat.S_IMODE(observed.st_mode)==mode, f'actual public input mode mismatch: {path}'

def _synthetic_sentence_block(group, sent_id, unique):
    return "\n".join([
        f"# newdoc id = {group}", f"# sent_id = {sent_id}",
        f"1\tWord{unique}\tlemma\tNOUN\t_\tNumber=Sing\t2\tnsubj\t_\t_",
        "2\ter\tvære\tAUX\t_\t_\t0\troot\t_\t_",
        "3\ttest\ttest\tNOUN\t_\tNumber=Sing\t2\tobj\t_\t_",
        "4\t.\t.\tPUNCT\t_\t_\t2\tpunct\t_\t_", "",
    ])

def _eligible_synthetic_source():
    groups = {role: [] for role in ("discovery", "calibration", "C1", "C2")}
    i = 0
    while any(len(rows) < 20 for rows in groups.values()):
        group = f"synthetic-{i}"
        role = n.role_for_group(("train", group))[0]
        if len(groups[role]) < 20:
            groups[role].append(group)
        i += 1
    blocks = [_synthetic_sentence_block(group, f"train-{i}", i)
              for i, group in enumerate(group for rows in groups.values() for group in rows)]
    def opaque(block):
        # The actual control code participates in history: generate synthetic
        # surface forms not present as short historical units. No gate is mocked.
        return block.replace("Word", "Z" + hashlib.sha256(b"synthetic surfaces").hexdigest()).replace(
            "\ter\t", "\t" + "q" + "xz" + "\t").replace(
            "\ttest\t", "\t" + "n" + "opquv" + "\t")
    return {
        n.SOURCE_FILES["train"]: opaque("\n".join(blocks)).encode(),
        n.SOURCE_FILES["dev"]: opaque(_synthetic_sentence_block("dev-extra", "dev-0", 1000)).encode(),
        n.SOURCE_FILES["test"]: opaque(_synthetic_sentence_block("test-extra", "test-0", 1001)).encode(),
        n.LICENSE_FILE: b"CC BY-SA 4.0\n",
    }

def _install_synthetic_git(monkeypatch, payloads, *, failure=None):
    import acquire_msae_independent_norspan_v1 as a
    blobs = {name: hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
             for name, payload in payloads.items()}
    calls = []
    def fake_run(argv, *, env, cwd=None):
        del env, cwd
        calls.append(argv)
        if "clone" in argv:
            if failure == "clone":
                return b"", b"synthetic failure", 128
            repo = Path(argv[-1]); repo.mkdir(); (repo / ".git").mkdir()
            return b"", b"", 0
        repo = Path(argv[argv.index("-C") + 1])
        if "checkout" in argv:
            for name, payload in payloads.items():
                (repo / name).write_bytes(payload)
            return b"", b"", 0
        if argv[-2:] == ["rev-parse", "HEAD"]:
            return (n.COMMIT + "\n").encode(), b"", 0
        if "rev-parse" in argv:
            return ("b" * 40 + "\n").encode(), b"", 0
        if "ls-tree" in argv:
            return b"".join(f"100644 blob {blobs[name]}\t{name}\0".encode()
                            for name in sorted(a.FILES)), b"", 0
        if "cat-file" in argv:
            return (b"".join(f"{oid} blob {len(payloads[name])}\n".encode()
                            for name, oid in sorted(blobs.items()))
                    + f"{n.COMMIT} commit 1\n{'b' * 40} tree 1\n".encode()), b"", 0
        return b"", b"", 0
    monkeypatch.setattr(a, "run", fake_run)
    return calls

class Fixture:
    def __init__(self, tmp_path, monkeypatch):
        assert str(tmp_path).startswith('/jumbo/lisp/f004ndc/tmp/lisplab1/')
        source_root = Path(__file__).resolve().parents[1]
        self.external = tmp_path / 'outside'; self.external.mkdir(mode=0o700)
        self.root = tmp_path / 'synthetic-project'; self.root.mkdir(mode=0o700)
        modes = {rel:mode for rel,mode in n.AUTHORITY_CONTROL_MODES.items()
                 if not rel.startswith('reports/provenance/')}
        modes.update({'TODO.md':0o644,'scripts/prepare_msae_independent_source_v10.py':0o755})
        for rel,mode in modes.items():
            _require_public_source_mode(source_root/rel,mode)
            target = self.root/rel; target.parent.mkdir(parents=True,exist_ok=True)
            raw = b'VERDICT: SHIP\nSYNTHETIC FIXTURE ONLY; not production review.\n' if rel == approval.IMPLEMENTATION_REVIEW else (source_root/rel).read_bytes()
            target.write_bytes(raw);target.chmod(mode)
        (self.root/'.git').mkdir();(self.root/'.git/HEAD').write_text('a'*40+'\n')
        for name,path in [('ROOT',self.root),('PROV',self.root/'reports/provenance/msae_independent_norspan_v1'),('DATA',self.root/'data/msae_independent_norspan_v1'),('RAW',self.root/'data/msae_independent_norspan_v1/raw'/n.COMMIT),('PRIVATE',self.root/'data/msae_independent_norspan_v1/private'),('CONFIG_PATH',self.root/'configs/msae_independent_norspan_v1/protocol.json')]:
            monkeypatch.setattr(n,name,path)
        def guard():
            assert n.ROOT == self.root and n.ROOT != source_root
            assert n.ROOT.parent == tmp_path and str(n.ROOT).startswith('/jumbo/lisp/f004ndc/tmp/lisplab1/')
        monkeypatch.setattr(n,'require_jpc_qualification',guard)
        monkeypatch.setattr(n,'_process_snapshot',lambda:{'scanned_process_count':1,'prohibited_match_count':0,'matches':[]})
        monkeypatch.setattr(n,'_git_porcelain_snapshot',lambda:{'outside_protocol_count':0,'outside_protocol_sha256':n.sha_bytes(b'[]')})
        private = self.external/'disposable-test-key.pem';self.private=private
        subprocess.run(['/usr/bin/openssl','genpkey','-algorithm','ED25519','-out',str(private)],check=True,capture_output=True);private.chmod(0o600)
        public = self.external/'test-public.der'
        subprocess.run(['/usr/bin/openssl','pkey','-in',str(private),'-pubout','-outform','DER','-out',str(public)],check=True,capture_output=True)
        self.key = public.read_bytes();self.sign_count=0
        statement={'schema_version':'norspan_signed_approval_v1','scope':'whole_implementation','verdict':'SHIP',
                   'subjects':{rel:{'sha256':hashlib.sha256((self.root/rel).read_bytes()).hexdigest(),'bytes':(self.root/rel).stat().st_size,'mode':mode} for rel,mode in modes.items()}}
        raw,sig = self.sign(statement)
        self.approvals = approval.Approvals(self.root,key=self.key,key_sha256=hashlib.sha256(self.key).hexdigest(),release=raw,release_signature=sig,release_sha256=hashlib.sha256(raw).hexdigest())
        self.session,self.store=c.CatalogStore.create(self.external/'catalogs',n.PROV,project_root=n.ROOT,lineage_sha256='f'*64)
        self.controller=c.Controller(self.session,self.store,self.approvals)
        reserve=r.reserve_scratch
        def synthetic_reserve(path,**kwargs):
            guard()
            cfg=r.load_client_contract(self.root)
            assert Path(path).parent == Path(cfg['scratch']['base'])
            return reserve(self.external/Path(path).name,**kwargs)
        monkeypatch.setattr(r,'reserve_scratch',synthetic_reserve)

    def sign(self,value):
        raw=r.canonical_bytes(value)+b'\n';path=self.external/f'statement-{self.sign_count}.json';sigpath=self.external/f'signature-{self.sign_count}.bin';self.sign_count+=1
        path.write_bytes(raw);path.chmod(0o644)
        subprocess.run(['/usr/bin/openssl','pkeyutl','-sign','-rawin','-inkey',str(self.private),'-in',str(path),'-out',str(sigpath)],check=True,capture_output=True);sigpath.chmod(0o644)
        return raw,sigpath.read_bytes()

    def history(self):self.controller.execute('build-history')

    def authority(self):
        self.history();self.controller.execute('build-authority')
        review=self.root/approval.AUTHORITY_REVIEW
        review.write_bytes(b'VERDICT: SHIP\nSYNTHETIC AUTHORITY REVIEW ONLY.\n');review.chmod(0o644)
        value={'schema_version':'norspan_signed_approval_v1','scope':'source_authority','verdict':'SHIP',
               'release_sha256':self.approvals.release_sha256,'lineage_sha256':self.session.lineage,
               'authority_pair':__import__('msae_jumbo_pair_commit').receipt_record(self.session.expected('authority.json')),
               'review_sha256':hashlib.sha256(review.read_bytes()).hexdigest()}
        raw,sig=self.sign(value);self.approvals.bind_authority(raw,sig,expected_sha256=hashlib.sha256(raw).hexdigest())

    def acquire(self,monkeypatch,*,license_bytes=None,failure=None):
        self.authority();payloads=_eligible_synthetic_source()
        if license_bytes is not None:payloads[n.LICENSE_FILE]=license_bytes
        self.calls=_install_synthetic_git(monkeypatch,payloads,failure=failure)
        return self.controller.execute('acquire')

    def fresh(self):
        session,store=c.CatalogStore.load(self.store.path,expected_sha256=self.store.sha256,root=n.PROV,project_root=n.ROOT,lineage_sha256=self.session.lineage)
        self.store=store  # retain explicit returned producer pin; never discover latest
        return c.Controller(session,store,self.approvals)
