# Maintained copy of independent source-free donor; original retained unchanged.
"""Independent source-free resource-contract regressions; current candidate RED."""
import hashlib
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r
import msae_norspan_jpc_controls as c
import prepare_msae_independent_norspan_v1 as p

def test_recovery_finite_physical_namespace_before_materializing_untrusted_names(tmp_path,monkeypatch):
 root=tmp_path/'controls';root.mkdir(mode=0o755);root.chmod(0o755)
 receipt=j.create_pair(root/'baseline.json',b'{}\n',mode=0o644)
 catalog={'schema_version':'norspan_jpc_custody_catalog_v1','lineage_sha256':'a'*64,'controls':{'baseline.json':j.receipt_record(receipt)}}
 pin=hashlib.sha256(r.canonical_bytes(catalog)).hexdigest()
 calls=[]
 def forbidden(fd):
  calls.append(fd)
  raise AssertionError('Unbounded os.listdir attempted before finite recovery physical-name admission')
 monkeypatch.setattr(os,'listdir',forbidden)
 result=r.recover_current_custody(root,catalog,expected_catalog_sha256=pin,lineage_sha256='a'*64)
 assert result['source_operations']==result['model_operations']==0 and calls==[]

def test_paired_prefix_validates_custody_without_buffering_entire_control(tmp_path,monkeypatch):
 root=tmp_path/'controls';root.mkdir(mode=0o755);root.chmod(0o755)
 monkeypatch.setattr(p,'PROV',root)
 session=c.ControlSession(root,lineage_sha256='a'*64)
 payload=b'prefix'+b'opaque-synthetic'*1024
 receipt=j.create_pair(root/'baseline.json',payload,mode=0o644);session.register('baseline.json',receipt)
 def forbidden(*args,**kwargs):
  raise AssertionError('Full paired-control read_bytes buffering attempted for requested prefix limit=1')
 # Streaming integrity checks may still hash ALL expected bytes; only buffering
 # the whole payload is prohibited. The actual pair.validate digest path stays.
 monkeypatch.setattr(j.OwnedPair,'read_bytes',forbidden)
 with p.paired_control_session(session):assert p.read_prefix_nofollow(root/'baseline.json',1)==payload[:1]
