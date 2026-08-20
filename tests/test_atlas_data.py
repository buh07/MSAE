import json
import os
import subprocess
import sys
import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_atlas_data import coarse_ner, validate_roles
from atlas_freeze import assert_role_access, verify_layer_trigger
import atlas_freeze


def test_common_ner_map():
    assert coarse_ner("B-person") == "PER"
    assert coarse_ner("I-corporation") == "ORG"
    assert coarse_ner("building") == "LOC"
    assert coarse_ner("creative-work") == "MISC"
    assert coarse_ner("O") == "O"


def test_frozen_roles_are_disjoint_and_group_offsets():
    roles = {}
    for role in ["discovery", "calibration", "C1", "C2"]:
        records = [json.loads(x) for x in (ROOT / f"data/atlas_v1/partitions/{role}.records.jsonl").read_text().splitlines()]
        units = [json.loads(x) for x in (ROOT / f"data/atlas_v1/partitions/{role}.units.jsonl").read_text().splitlines()]
        roles[role] = {x["content_hash"] for x in records}
        counts = {}
        for unit in units:
            counts[unit["base_id"]] = counts.get(unit["base_id"], 0) + 1
            assert len(unit["input_ids"]) == len(unit["absolute_labels"]["abs_pos_16"])
            assert len(unit["input_ids"]) <= 128
        assert set(counts.values()) == {4}
    names = list(roles)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            assert not (roles[left] & roles[right])


def test_final_unlock_absent():
    assert not (ROOT / ".atlas_final_unlock").exists()
    try:
        assert_role_access("final")
    except PermissionError:
        pass
    else:
        raise AssertionError("final role unexpectedly unlocked")


def test_private_final_is_ignored_and_restrictive():
    private = ROOT / "data/atlas_v1/private"
    assert (private.stat().st_mode & 0o077) == 0
    assert all((path.stat().st_mode & 0o077) == 0 for path in private.iterdir() if path.is_file())
    result = subprocess.run(["git", "check-ignore", "-q", str(private / "final.records.jsonl")], cwd=ROOT)
    assert result.returncode == 0


def test_real_document_groups_do_not_cross_c1_c2():
    def groups(role):
        return {json.loads(line)["document_group"] for line in (ROOT / f"data/atlas_v1/partitions/{role}.records.jsonl").read_text().splitlines()}
    assert not (groups("C1") & groups("C2"))


def test_production_firewall_rejects_cross_role_document_fixture():
    def record(role, base, group):
        return {"base_id": base, "content_hash": f"hash-{role}", "document_group": group,
                "words": ["x"], "labels": {"dummy": ["x"]}}

    records = {"left": [record("left", "left-1", "cloned-document")],
               "right": [record("right", "right-1", "cloned-document")]}
    units = {role: [{"base_id": rows[0]["base_id"]} for _ in range(4)]
             for role, rows in records.items()}
    result = validate_roles(records, units)
    assert result["passed"] is False
    assert "document_group overlap left/right" in result["failures"]


def test_layer_trigger_cannot_omit_calibration_bundles(tmp_path):
    trigger = tmp_path / "layer_trigger_freeze.json"
    trigger.write_text(json.dumps({"schema_version": "atlas_v1_layer_trigger",
                                   "l4_fallback_activated": False, "primary_layer": 3, "descriptive_layer": 4,
                                   "prescore_bundle_sha256": "candidate",
                                   "calibration_bundle_sha256": {}}))
    try:
        verify_layer_trigger(trigger, {"bundle_sha256": "candidate"})
    except RuntimeError as exc:
        assert "exactly L3 and L4" in str(exc)
    else:
        raise AssertionError("empty calibration-bundle map bypassed trigger verification")


def test_final_unlock_still_verifies_private_payload(tmp_path, monkeypatch):
    (tmp_path / "configs/atlas").mkdir(parents=True)
    private = tmp_path / "data/private.jsonl"
    private.parent.mkdir()
    private.write_text('{"blind":true}\n')
    digest = hashlib.sha256(private.read_bytes()).hexdigest()
    manifest = {"files": {"data/private.jsonl": {"access": "M8_only_unlock_required", "sha256": digest}}}
    (tmp_path / "configs/atlas/partition_hashes.json").write_text(json.dumps(manifest))
    (tmp_path / ".atlas_final_unlock").write_text(atlas_freeze.UNLOCK_TEXT)
    monkeypatch.setattr(atlas_freeze, "ROOT", tmp_path)
    atlas_freeze.assert_role_access("final")
    private.write_text('{"blind":false}\n')
    with pytest.raises(RuntimeError, match="blind final artifact differs"):
        atlas_freeze.assert_role_access("final")
