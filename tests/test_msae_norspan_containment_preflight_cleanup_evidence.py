"""Nested cleanup evidence regression; local regular files, no active kernel arm."""
from test_msae_norspan_containment_preflight import load,fake_cgroups
import os
import json


def test_final_membership_read_primary_retains_after_release_close_secondary(tmp_path,monkeypatch):
    p=load();before=p.fd_snapshot();fake_cgroups(p,tmp_path,monkeypatch)
    primary=OSError(5,'synthetic final membership-read primary')
    secondary=OSError(5,'synthetic final control-close secondary')
    phase=[];target=[];read_fired=[];close_fired=[]
    opening,reading,closing=os.open,os.read,os.close
    def open(name,flags,*args,**kwargs):
        fd=opening(name,flags,*args,**kwargs)
        if phase and name=='cgroup.procs' and not target:target.append(fd)
        return fd
    def read(fd,count):
        if target and fd==target[0] and not read_fired:
            read_fired.append(True);raise primary
        return reading(fd,count)
    def close(fd):
        closing(fd)
        if target and fd==target[0] and not close_fired:
            close_fired.append(True);raise secondary
    def inert(*args,**kwargs):
        phase.append(True)
        return {'status':'UNAVAILABLE_SELF_MIGRATION','result':{'returncode':-1,'errno':13,'before':'inert','after':'inert'},'owned_child_reaped':True}
    monkeypatch.setattr(os,'open',open);monkeypatch.setattr(os,'read',read);monkeypatch.setattr(os,'close',close);monkeypatch.setattr(p,'parked',inert)
    result=p.cgroup_preflight({})
    assert result['status']=='BLOCKED_UNKNOWN' and read_fired and close_fired
    assert 'membership-read primary' in json.dumps(result)
    assert 'control-close secondary' in json.dumps(result),'nested secondary note lost'
    assert result['cleanup_errors'][0]['notes']==primary.__notes__
    assert p.fd_snapshot()==before
