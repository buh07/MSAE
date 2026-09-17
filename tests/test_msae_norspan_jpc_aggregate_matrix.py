# Maintained independent synthetic counterexample matrix; original unchanged.
"""Independent final-digest metadata/alias/ancestry faults in fresh opaque pairs."""
import hashlib
import os
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_jumbo_pair_commit as j
import msae_norspan_jpc_runtime as r

@pytest.mark.parametrize("kind", ["flat_publish", "flat_verify", "role_publish", "role_verify", "recovery"])
@pytest.mark.parametrize("attack", ["same_size_restored_mtime", "third_alias", "stage_substitution", "ancestor_mode"])
def test_last_digest_cannot_bless_earlier_alias_metadata_ancestor(tmp_path,monkeypatch,kind,attack):
    root=tmp_path/"aggregate"; first=root/"one"; final_name="two"
    if kind.startswith("role"):
        first=root/"discovery"/"payload.jsonl"; final_name="payload.jsonl"
        values={role:b"aaaa" for role in r.ROLES}
        if kind=="role_verify": values=r.publish_role_pairs(root,values)
        def operation():
            if kind=="role_verify": return r.verify_role_pairs(root,values,durable=True)
            return r.publish_role_pairs(root,values)
    elif kind.startswith("flat"):
        values={"one":b"aaaa","two":b"zzzz"}
        if kind=="flat_verify": values=r.publish_flat_pairs(root,values,directory_mode=0o700,file_mode=0o644)
        def operation():
            if kind=="flat_verify": return r.verify_flat_pairs(root,values,directory_mode=0o700,file_mode=0o644,durable=True)
            return r.publish_flat_pairs(root,values,directory_mode=0o700,file_mode=0o644)
    else:
        root.mkdir(mode=0o700); first=root/"baseline.json"; final_name="authority.json"
        values={"schema_version":"norspan_jpc_custody_catalog_v1","lineage_sha256":"a"*64,
                "controls":{name:j.receipt_record(j.create_pair(root/name,b"aaaa",mode=0o644))
                            for name in ["baseline.json","authority.json"]}}
        digest=hashlib.sha256(r.canonical_bytes(values)).hexdigest()
        def operation():
            return r.recover_current_custody(root,values,expected_catalog_sha256=digest,lineage_sha256="a"*64)
    real_validate,real_pread=j.OwnedPair.validate,os.pread
    armed,fired=[],[]
    def validate(pair,*,durable=False):
        is_last=pair.receipt.final_name==final_name
        if kind.startswith("role"): is_last=is_last and os.readlink(f"/proc/self/fd/{pair.fd}").startswith(str(root/"c2")+"/")
        if durable and is_last: armed.append(True)
        return real_validate(pair,durable=durable)
    def pread(fd,size,offset):
        result=real_pread(fd,size,offset)
        if armed and not fired:
            fired.append(True)
            if attack=="same_size_restored_mtime":
                old=first.stat(); first.write_bytes(b"bbbb"); os.utime(first,ns=(old.st_atime_ns,old.st_mtime_ns))
            elif attack=="third_alias":
                os.link(first,first.parent/"foreign-third-link")
            elif attack=="stage_substitution":
                stage=first.parent/("."+first.name+".stage")
                stage.rename(first.parent/"retained-original-stage")
                stage.write_bytes(b"aaaa")
            else:
                first.parent.chmod(0o755)
        return result
    before=set(os.listdir("/proc/self/fd"))
    monkeypatch.setattr(j.OwnedPair,"validate",validate); monkeypatch.setattr(os,"pread",pread)
    with pytest.raises((r.RuntimeBlocked,j.PairFailure)):
        operation()
    assert fired==[True]
    assert set(os.listdir("/proc/self/fd"))==before
    assert first.exists()
    if attack=="same_size_restored_mtime": assert first.read_bytes()==b"bbbb"
    elif attack=="third_alias": assert (first.parent/"foreign-third-link").exists()
    elif attack=="stage_substitution": assert (first.parent/"retained-original-stage").exists()
    else: assert first.parent.stat().st_mode&0o777==0o755
