from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("known_ioi", ROOT / "scripts/known_mechanism_ioi_v1.py")
assert SPEC and SPEC.loader
ioi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ioi)
CFG = json.loads((ROOT / "configs/known_mechanism_ioi_v1/run.json").read_text())


def test_panel_balance_and_heldout_disjointness() -> None:
    dev = ioi.raw_rows(CFG, "development")
    confirmation = ioi.raw_rows(CFG, "confirmation")
    assert len(dev) == 256
    assert len(confirmation) == 128
    for rows, template_count in ((dev, 4), (confirmation, 2)):
        assert {sum(r["template_index"] == t and r["set_index"] == s for r in rows) for t in range(template_count) for s in range(4)} == {16}
        for t in range(template_count):
            for s in range(4):
                subset = [r for r in rows if r["template_index"] == t and r["set_index"] == s]
                names = CFG["panel"][rows[0]["stage"]]["names"][s * 8 : (s + 1) * 8]
                assert {r["answer_a"] for r in subset} == set(names)
                assert {r["answer_b"] for r in subset} == set(names)
                assert all(sum(r["answer_a"] == name for r in subset) == 2 for name in names)
                assert all(sum(r["answer_b"] == name for r in subset) == 2 for name in names)
    for field in ("names", "places", "objects", "templates"):
        assert not set(CFG["panel"]["development"][field]) & set(CFG["panel"]["confirmation"][field])


def test_counterfactual_and_sham_semantics() -> None:
    row = ioi.raw_rows(CFG, "development")[0]
    assert row["answer_a"] != row["answer_b"]
    assert row["base_prompt"] != row["counterfactual_prompt"]
    assert row["base_prompt"] != row["sham_prompt"]
    assert row["answer_a"] in row["base_prompt"] and row["answer_b"] in row["base_prompt"]
    assert row["answer_a"] in row["counterfactual_prompt"] and row["answer_b"] in row["counterfactual_prompt"]
    assert row["answer_a"] in row["sham_prompt"] and row["answer_b"] in row["sham_prompt"]
    assert row["place"] not in row["sham_prompt"] and row["object"] not in row["sham_prompt"]


def metric_rows(value: float, field: str, informative: bool = True) -> list[dict]:
    return [
        {"template_index": t, "set_index": s, "row_index": r, "component_id": f"{t}:{s}:{r}", "informative": informative, field: value if informative else None}
        for t in range(4) for s in range(4) for r in range(16)
    ]


def test_behavior_metric_signs_and_effect_floor_are_strict() -> None:
    rows = [{"stage": "development", "template_index": 0, "set_index": 0, "row_index": i, "component_id": str(i), "component_block": "x", "answer_a_id": 0, "answer_b_id": 1} for i in range(2)]
    base = np.asarray([[1.0, 0.0], [0.5, 0.0]])
    counter = np.asarray([[0.0, 1.0], [0.0, 0.5]])
    sham = np.asarray([[0.9, 0.0], [0.5, 0.0]])
    result = ioi.behavior_metrics(rows, base, counter, sham, 0.5)
    assert result[0]["informative"] is True
    assert result[0]["counterfactual_advantage"] == pytest.approx(1.0)
    assert result[0]["sham_ratio"] == pytest.approx(0.1)
    assert result[1]["informative"] is False  # equality does not clear the frozen floor


def test_patch_metric_oracle() -> None:
    rows = [{"stage": "development", "template_index": 0, "set_index": 0, "row_index": 0, "component_id": "x", "component_block": "x", "answer_a_id": 0, "answer_b_id": 1}]
    behavior = [{"informative": True, "base_advantage": 2.0, "counterfactual_a_minus_b": -2.0}]
    counter_patch = np.asarray([[-2.0, 0.0]])
    sham_patch = np.asarray([[1.8, 0.0]])
    result = ioi.patch_metrics(rows, behavior, counter_patch, sham_patch)[0]
    assert result["recovery"] == pytest.approx(1.0)
    assert result["sham_movement"] == pytest.approx(0.05)


def test_hierarchical_bootstrap_is_deterministic_and_grouped() -> None:
    rows = metric_rows(0.1, "sham_ratio")
    first = ioi.hierarchical_interval(rows, "sham_ratio", 50, 9)
    second = ioi.hierarchical_interval(rows, "sham_ratio", 50, 9)
    assert first == second
    assert first == {"point": pytest.approx(0.1), "lower": pytest.approx(0.1), "upper": pytest.approx(0.1), "draws": 50}


def test_behavior_gate_strict_upper_and_support() -> None:
    good = metric_rows(0.2, "sham_ratio")
    assert ioi.summarize_behavior(good, CFG["behavior_gate"], 1)["pass"] is True
    boundary = metric_rows(0.35, "sham_ratio")
    assert ioi.summarize_behavior(boundary, CFG["behavior_gate"], 1)["pass"] is False
    under = metric_rows(0.1, "sham_ratio")
    for row in under:
        if row["template_index"] == 0 and row["set_index"] == 0 and row["row_index"] >= 13:
            row["informative"] = False
            row["sham_ratio"] = None
    assert ioi.summarize_behavior(under, CFG["behavior_gate"], 1)["pass"] is False


def test_patch_gate_thresholds() -> None:
    rows = metric_rows(0.9, "recovery")
    for row in rows:
        row["sham_movement"] = 0.1
    assert ioi.summarize_patch(rows, CFG["patch_gate"], 2)["pass"] is True
    for row in rows:
        row["recovery"] = 0.6
    assert ioi.summarize_patch(rows, CFG["patch_gate"], 2)["pass"] is False


class FakeBlock(nn.Module):
    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        return hidden


class FakeLM(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.transformer = SimpleNamespace(h=nn.ModuleList([FakeBlock()]))

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, use_cache: bool = False) -> SimpleNamespace:
        del attention_mask, use_cache
        hidden = torch.nn.functional.one_hot(input_ids, num_classes=4).float()
        hidden = self.transformer.h[0](hidden)
        return SimpleNamespace(logits=hidden)


def test_full_state_hook_replaces_exact_final_token() -> None:
    rows = [
        {"base_prompt_ids": [1, 2], "answer_a_id": 0, "answer_b_id": 1},
        {"base_prompt_ids": [2, 3], "answer_a_id": 0, "answer_b_id": 1},
    ]
    donor = np.asarray([[1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0]], np.float32)
    logits, captured = ioi.forward_condition(FakeLM(), rows, "base", 0, 2, 0, torch.device("cpu"), donor=donor)
    assert np.array_equal(logits, donor)
    assert np.array_equal(captured, np.asarray([[0, 0, 1, 0], [0, 0, 0, 1]], np.float32))


def test_model_specific_and_two_family_logic_is_frozen() -> None:
    assert CFG["behavior_gate"]["minimum_families"] == 2
    assert CFG["patch_gate"]["minimum_families"] == 2
    assert CFG["confirmation_gate"]["minimum_families"] == 2
    assert len({m["family"] for m in CFG["models"]}) == 3


def test_confirmation_waits_before_loading_or_reading_rows() -> None:
    source = (ROOT / "scripts/known_mechanism_ioi_v1.py").read_text()
    body = source[source.index("def run_confirmation"):source.index("def final")]
    assert body.index("wait_for([gate_path]") < body.index("load_model(spec")
    assert body.index("if not gate[") < body.index("confirmation_{model_key}.jsonl")
    assert body.index("if not gate[") < body.index("include_confirmation=True")


def test_terminal_waiter_propagates_failure_and_times_out(tmp_path: Path) -> None:
    failed = tmp_path / "failed"
    failed.mkdir()
    ioi.exjson(failed / "FAILED.json", {"error": "boom"})
    with pytest.raises(RuntimeError, match="upstream failure"):
        ioi.wait_for_terminals([failed], ["COMPLETE.json", "BLOCKED.json"], timeout=0, poll=0)
    silent = tmp_path / "silent"
    silent.mkdir()
    with pytest.raises(TimeoutError, match="timeout waiting"):
        ioi.wait_for_terminals([silent], ["COMPLETE.json", "BLOCKED.json"], timeout=0, poll=0)
    complete = tmp_path / "complete"
    complete.mkdir()
    ioi.exjson(complete / "COMPLETE.json", {"status": "ok"})
    assert ioi.wait_for_terminals([complete], ["COMPLETE.json", "BLOCKED.json"], timeout=0, poll=0)[complete].name == "COMPLETE.json"


def _minimal_gate_config(tmp_path: Path) -> Path:
    value = {
        "models": [{"key": "model", "family": "family"}],
        "runtime": {"output_root": "out", "gate_timeout_seconds": 0, "gate_poll_seconds": 0, "freeze": "freeze.json"},
        "patch_gate": {"minimum_families": 2},
        "confirmation_gate": {"minimum_families": 2},
        "seed": 1,
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(value))
    return path


def test_patch_aggregator_emits_failure_after_failed_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _minimal_gate_config(tmp_path)
    monkeypatch.setattr(ioi, "ROOT", tmp_path)
    monkeypatch.setattr(ioi, "verify_freeze", lambda *args, **kwargs: {})
    ioi.exjson(tmp_path / "out/gates/behavior/result.json", {"general_gate_pass": True})
    worker = tmp_path / "out/development/patch/model"
    worker.mkdir(parents=True)
    ioi.exjson(worker / "FAILED.json", {"error": "worker died"})
    with pytest.raises(RuntimeError, match="upstream failure"):
        ioi.patch_gate(config)
    assert (tmp_path / "out/gates/patch/FAILED.json").is_file()


def test_patch_aggregator_emits_timeout_after_silent_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _minimal_gate_config(tmp_path)
    monkeypatch.setattr(ioi, "ROOT", tmp_path)
    monkeypatch.setattr(ioi, "verify_freeze", lambda *args, **kwargs: {})
    ioi.exjson(tmp_path / "out/gates/behavior/result.json", {"general_gate_pass": True})
    (tmp_path / "out/development/patch/model").mkdir(parents=True)
    with pytest.raises(TimeoutError, match="timeout waiting"):
        ioi.patch_gate(config)
    assert (tmp_path / "out/gates/patch/FAILED.json").is_file()


def test_final_aggregator_emits_failure_after_confirmation_worker_death(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _minimal_gate_config(tmp_path)
    monkeypatch.setattr(ioi, "ROOT", tmp_path)
    monkeypatch.setattr(ioi, "verify_freeze", lambda *args, **kwargs: {})
    ioi.exjson(tmp_path / "out/gates/patch/result.json", {"general_gate_pass": True, "status": "PASS"})
    worker = tmp_path / "out/confirmation/model"
    worker.mkdir(parents=True)
    ioi.exjson(worker / "FAILED.json", {"error": "worker died"})
    with pytest.raises(RuntimeError, match="upstream failure"):
        ioi.final(config)
    assert (tmp_path / "out/final/FAILED.json").is_file()


def test_final_aggregator_emits_timeout_after_silent_confirmation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _minimal_gate_config(tmp_path)
    monkeypatch.setattr(ioi, "ROOT", tmp_path)
    monkeypatch.setattr(ioi, "verify_freeze", lambda *args, **kwargs: {})
    ioi.exjson(tmp_path / "out/gates/patch/result.json", {"general_gate_pass": True, "status": "PASS"})
    (tmp_path / "out/confirmation/model").mkdir(parents=True)
    with pytest.raises(TimeoutError, match="timeout waiting"):
        ioi.final(config)
    assert (tmp_path / "out/final/FAILED.json").is_file()


def test_behavior_gate_rejects_tampered_completion_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _minimal_gate_config(tmp_path)
    monkeypatch.setattr(ioi, "ROOT", tmp_path)
    monkeypatch.setattr(ioi, "verify_freeze", lambda *args, **kwargs: {"candidate_inventory_sha256": "inventory"})
    (tmp_path / "freeze.json").write_text("frozen")
    root = tmp_path / "out/development/behavior/model"
    root.mkdir(parents=True)
    (root / "metrics.jsonl").write_text("{}\n")
    with (root / "activations.npz").open("wb") as handle:
        np.savez(handle, base=np.zeros((1, 1)))
    ioi.exjson(root / "COMPLETE.json", {
        "schema_version": "known_mechanism_ioi_v1_behavior_complete", "model": "model", "rows": 256,
        "metrics_sha256": "tampered", "activations_sha256": ioi.sha(root / "activations.npz"),
        "freeze_sha256": ioi.sha(tmp_path / "freeze.json"), "freeze_inventory_sha256": "inventory",
        "model_forwards": True, "training": False, "representation_methods": False,
    })
    with pytest.raises(RuntimeError, match="artifact mismatch"):
        ioi.behavior_gate(config)
    assert (tmp_path / "out/gates/behavior/FAILED.json").is_file()


def test_create_once_artifacts_reject_duplicate_namespace(tmp_path: Path) -> None:
    artifact = tmp_path / "manifest.json"
    ioi.exjson(artifact, {"first": True})
    with pytest.raises(FileExistsError):
        ioi.exjson(artifact, {"second": True})
    assert json.loads(artifact.read_text()) == {"first": True}


def test_scope_closes_old_line_and_forbids_methods_training() -> None:
    scope = CFG["scope"]
    assert scope["representation_methods"] is False
    assert scope["training"] is False
    assert scope["v6_3_prompt_retry"] is False
    assert scope["future_method_authorization_in_this_run"] is False
    assert "configs/behavioral_endpoint_v6_3" in CFG["preservation"]["forbid_paths"]


def test_launcher_has_no_training_or_representation_method_jobs() -> None:
    launcher = (ROOT / "scripts/launch_known_mechanism_ioi_v1_tmux.sh").read_text()
    assert "CUDA_VISIBLE_DEVICES='$uuid'" in launcher
    assert "EXPECTED_GPU_UUID='$uuid'" in launcher
    assert "train" not in launcher.lower()
    assert "method-worker" not in launcher
