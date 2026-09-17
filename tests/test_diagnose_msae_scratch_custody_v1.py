"""Preserve predecessor counterexamples separately from current refusal checks.

Legacy reproduction passes mean the frozen predecessor is unsafe, NOT current
production approval. Current tests prove refusal, not complete runner qualification.
All manipulated bytes are fresh synthetic data with retained before-images.
"""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import diagnose_msae_scratch_custody_v1 as d
sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
import msae_norspan_legacy_cleanup as legacy


@pytest.mark.parametrize("case", ["foreign_extra", "checked_then_substituted"])
def test_frozen_legacy_cleanup_foreign_loss_with_retained_before_images(tmp_path, monkeypatch, case):
    monkeypatch.setattr(d, "acquisition", legacy)
    assert tmp_path.parts[:2] == ("/", "jumbo")
    result = d.probe(tmp_path, case)
    assert result["result"] == "FAIL destructive synthetic foreign cleanup"
    assert result["foreign_name_preserved"] is False
    assert (tmp_path / case / "foreign_before_image").read_bytes() == b"fixed injected foreign evidence\n"
    assert (tmp_path / case / "owned_before_image").read_bytes() == b"fixed owned synthetic evidence\n"
    if case == "checked_then_substituted":
        assert result["injected"][0]["replacement_inode"] != result["injected"][0]["checked_inode"]
        assert result["error"]["errno"] == 39
        assert (tmp_path / case / "scratch/retained-original").read_bytes() == b"fixed owned synthetic evidence\n"
    else:
        assert result["error"] is None
        assert not (tmp_path / case / "scratch").exists()


@pytest.mark.parametrize("case", ["foreign_extra", "checked_then_substituted"])
def test_current_cleanup_interface_refuses_without_deleting_any_name(tmp_path, case):
    result = d.probe(tmp_path, case)
    scratch = tmp_path / case / "scratch"
    assert result["result"] == "preserved"
    assert result["error"]["message"] == "scratch_deletion_prohibited_jpc"
    assert result["injected"] == []  # no unlink, therefore no substitution trigger
    assert (scratch / "tracked").read_bytes() == b"fixed owned synthetic evidence\n"
    if case == "foreign_extra":
        assert (scratch / "foreign").read_bytes() == b"fixed injected foreign evidence\n"


def test_cli_refuses_preexisting_root_without_modification(tmp_path, monkeypatch):
    protected = tmp_path / "existing"; protected.mkdir()
    (protected / "sentinel").write_bytes(b"retain")
    monkeypatch.setattr(sys, "argv", ["diagnostic", "--root", str(protected)])
    with pytest.raises(FileExistsError): d.main()
    assert list(protected.iterdir()) == [protected / "sentinel"]
    assert (protected / "sentinel").read_bytes() == b"retain"


def test_cli_refuses_nonjumbo_root_before_creation(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["diagnostic", "--root", "/tmp/forbidden-scratch-diagnostic"])
    with pytest.raises(RuntimeError, match="fresh_absolute_jumbo_root_required"): d.main()
