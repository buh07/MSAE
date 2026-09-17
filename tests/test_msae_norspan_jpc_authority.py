"""Synthetic signatures only: these keys never establish production authority."""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import msae_norspan_jpc_runtime as r
import msae_norspan_jpc_authority as a


def test_fixture_rejects_invalid_actual_public_mode_before_copy(tmp_path):
    from msae_norspan_controller_fixture import _require_public_source_mode
    public=tmp_path/'ordinary-public';public.write_bytes(b'synthetic public fixture')
    public.chmod(0o700)
    with pytest.raises(AssertionError,match='actual public input mode mismatch'):
        _require_public_source_mode(public,0o644)
    assert public.stat().st_mode & 0o777 == 0o700
    public.chmod(0o644)
    _require_public_source_mode(public,0o644)


def signed(tmp_path, value):
    assert str(tmp_path).startswith('/jumbo/lisp/f004ndc/tmp/lisplab1/')
    private = tmp_path / 'disposable-test-key.pem'
    public = tmp_path / 'disposable-test-public.der'
    statement = tmp_path / 'test-statement.json'
    signature = tmp_path / 'test-signature.bin'
    subprocess.run(['/usr/bin/openssl', 'genpkey', '-algorithm', 'ED25519', '-out', str(private)], check=True, capture_output=True)
    subprocess.run(['/usr/bin/openssl', 'pkey', '-in', str(private), '-pubout', '-outform', 'DER', '-out', str(public)], check=True, capture_output=True)
    raw = r.canonical_bytes(value) + b'\n'
    statement.write_bytes(raw)
    subprocess.run(['/usr/bin/openssl', 'pkeyutl', '-sign', '-rawin', '-inkey', str(private), '-in', str(statement), '-out', str(signature)], check=True, capture_output=True)
    private.chmod(0o600)
    return public.read_bytes(), raw, signature.read_bytes()


def test_genuine_detached_signature_verifies_immutable_copies(tmp_path):
    key, raw, sig = signed(tmp_path, {'purpose': 'synthetic-test-only'})
    assert a.verify_signature(key, raw, sig, key_sha256=hashlib.sha256(key).hexdigest()) is None


@pytest.mark.parametrize('fault', ['wrong_pin', 'wrong_key', 'wrong_statement', 'wrong_sig', 'short_key', 'short_sig'])
def test_signature_binding_rejects_all_mutations(tmp_path, fault):
    key, raw, sig = signed(tmp_path, {'purpose': 'synthetic-test-only'})
    pin = hashlib.sha256(key).hexdigest()
    if fault == 'wrong_pin': pin = '0' * 64
    elif fault == 'wrong_key': key = key[:-1] + bytes([key[-1] ^ 1]); pin = hashlib.sha256(key).hexdigest()
    elif fault == 'wrong_statement': raw += b' '
    elif fault == 'wrong_sig': sig = sig[:-1] + bytes([sig[-1] ^ 1])
    elif fault == 'short_key': key = key[:-1]
    else: sig = sig[:-1]
    with pytest.raises(r.RuntimeBlocked): a.verify_signature(key, raw, sig, key_sha256=pin)


def test_signature_failure_closes_every_owned_memfd(tmp_path, monkeypatch):
    key, raw, sig = signed(tmp_path, {'purpose': 'synthetic-test-only'})
    before = set(os.listdir('/proc/self/fd'))
    def fail(*args, **kwargs): raise KeyboardInterrupt('synthetic-interruption')
    monkeypatch.setattr(a.subprocess, 'run', fail)
    with pytest.raises(KeyboardInterrupt): a.verify_signature(key, raw, sig, key_sha256=hashlib.sha256(key).hexdigest())
    assert set(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('boundary',['write','seal'])
@pytest.mark.parametrize('error',[OSError,KeyboardInterrupt])
def test_signature_input_setup_faults_release_fds_without_starting_child(tmp_path,monkeypatch,boundary,error):
    key,raw,sig=signed(tmp_path,{'purpose':'synthetic setup fault'})
    before=set(os.listdir('/proc/self/fd'));fired=[]
    def fault(*args,**kwargs):fired.append(boundary);raise error('synthetic memfd '+boundary)
    if boundary=='write':monkeypatch.setattr(os,'write',fault)
    else:monkeypatch.setattr(a.fcntl,'fcntl',fault)
    def forbidden(*args,**kwargs):raise AssertionError('setup failure started child')
    monkeypatch.setattr(a.subprocess,'run',forbidden)
    with pytest.raises(error):a.verify_signature(key,raw,sig,key_sha256=hashlib.sha256(key).hexdigest())
    assert fired==[boundary] and set(os.listdir('/proc/self/fd'))==before


def test_signature_interrupt_after_live_child_spawn_kills_reaps_and_releases_fds(tmp_path,monkeypatch):
    key,raw,sig=signed(tmp_path,{'purpose':'synthetic spawned child interruption'})
    before=set(os.listdir('/proc/self/fd'));children=[];popen=subprocess.Popen
    def child(argv,**kwargs):
        assert argv[:4]==['/usr/bin/openssl','pkeyutl','-verify','-rawin']
        # Substitute only the external child producer, not run's kill/reap logic.
        process=popen([sys.executable,'-c','import time; time.sleep(60)'],**kwargs)
        children.append(process)
        assert process.poll() is None
        def interrupted(*args,**kwargs):raise KeyboardInterrupt('synthetic live child interruption')
        process.communicate=interrupted
        return process
    monkeypatch.setattr(subprocess,'Popen',child)
    with pytest.raises(KeyboardInterrupt):a.verify_signature(key,raw,sig,key_sha256=hashlib.sha256(key).hexdigest())
    assert len(children)==1 and children[0].returncode is not None
    with pytest.raises(ChildProcessError):os.waitpid(children[0].pid,os.WNOHANG)
    assert set(os.listdir('/proc/self/fd'))==before
