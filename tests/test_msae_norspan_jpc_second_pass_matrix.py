# Maintained independent synthetic counterexample matrix; original unchanged.
"""Independent final-pass scheduling of real fresh synthetic scratch mutations."""
import os
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_norspan_jpc_runtime as r
import msae_jumbo_pair_commit as j

@pytest.mark.parametrize("kind", ["home_foreign", "earlier_file_over_budget"])
@pytest.mark.parametrize("durable", [False, True])
@pytest.mark.parametrize("pass_number", [1, 2])
def test_scratch_mutation_during_each_final_inventory_pass_rejects(tmp_path, monkeypatch, kind, durable, pass_number):
    with r.reserve_scratch(tmp_path/"lease", authority_sha256="a"*64, entry_lineage_sha256="b"*64) as scratch:
        repo = scratch.path/"repo"; repo.mkdir(mode=0o700)
        first = repo/"one"; first.write_bytes(b"aaaa")
        (repo/"two").write_bytes(b"zzzz")
        real_validate, real_stat = r._Directory.validate, os.stat
        armed, hits, fired = [], [], []
        def validate(directory, names=None, *, durable=False):
            result = real_validate(directory, names, durable=durable)
            if directory is scratch and names == {"home", "repo"}:
                armed.append(True)
            return result
        def named_stat(name, *args, **kwargs):
            result = real_stat(name, *args, **kwargs)
            if armed and name == "two":
                hits.append(True)
                if len(hits) == pass_number:
                    fired.append(True)
                    if kind == "home_foreign":
                        (scratch.path/"home"/"foreign").write_bytes(b"foreign")
                    else:
                        first.write_bytes(b"over-budget-synthetic-bytes")
            return result
        monkeypatch.setattr(r._Directory, "validate", validate)
        monkeypatch.setattr(os, "stat", named_stat)
        with pytest.raises((r.RuntimeBlocked, j.PairFailure)):
            result = scratch.snapshot(durable=durable, file_bytes=4, total_bytes=8, entries=10)
            assert fired == [True]
            if kind == "home_foreign":
                assert (scratch.path/"home"/"foreign").read_bytes() == b"foreign"
            else:
                assert first.stat().st_size > 4
            pytest.fail("False final-pass scratch custody: " + repr(result))
        assert fired == [True]

@pytest.mark.parametrize("close_type", [OSError, KeyboardInterrupt])
def test_scratch_final_pass_budget_fault_plus_all_release_errors_keeps_budget_primary(tmp_path, monkeypatch, close_type):
    scratch = r.reserve_scratch(tmp_path/"lease", authority_sha256="a"*64, entry_lineage_sha256="b"*64)
    repo=scratch.path/"repo"; repo.mkdir(mode=0o700)
    first=repo/"one"; first.write_bytes(b"aaaa"); (repo/"two").write_bytes(b"zzzz")
    sentinel=tmp_path/"unrelated"; sentinel.write_bytes(b"unrelated")
    real_validate,real_stat,real_close,real_finish=r._Directory.validate,os.stat,os.close,j._finish
    armed,hits,fired,attempts,reused=[],[],[],[],[]
    expected=[scratch.fd,*reversed(scratch.parent.descriptors)]
    def validate(directory,names=None,*,durable=False):
        result=real_validate(directory,names,durable=durable)
        if directory is scratch and names=={"home","repo"}: armed.append(True)
        return result
    def named_stat(name,*args,**kwargs):
        result=real_stat(name,*args,**kwargs)
        if armed and name=="two":
            hits.append(True)
            if len(hits)==2:
                fired.append(True); first.write_bytes(b"over-budget-synthetic-bytes")
        return result
    def finish(parent,owned,primary):
        if owned!=scratch.fd: return real_finish(parent,owned,primary)
        def fail_close(fd):
            attempts.append(fd); real_close(fd)
            reused.append(os.open(sentinel,os.O_RDONLY))
            raise close_type("secondary-close-"+str(fd))
        with monkeypatch.context() as patch:
            patch.setattr(os,"close",fail_close)
            return real_finish(parent,owned,primary)
    monkeypatch.setattr(r._Directory,"validate",validate)
    monkeypatch.setattr(os,"stat",named_stat)
    monkeypatch.setattr(j,"_finish",finish)
    try:
        caught = None
        try:
            with scratch:
                scratch.snapshot(durable=True,file_bytes=4,total_bytes=8,entries=10)
        except BaseException as exc:
            caught = exc
        assert fired==[True] and attempts==expected
        assert first.read_bytes()==b"over-budget-synthetic-bytes"
        for fd in reused: assert os.pread(fd,20,0)==b"unrelated"
        assert isinstance(caught,(r.RuntimeBlocked,j.PairFailure)), (
            "Missing scratch validation primary; actual primary is "+repr(caught))
        notes=" ".join(getattr(caught,"__notes__",[]))
        assert all("secondary-close-"+str(fd) in notes for fd in expected)
    finally:
        for fd in reused: real_close(fd)
        if not scratch.closed: scratch.close()
