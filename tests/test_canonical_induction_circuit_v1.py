from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("induction", ROOT / "scripts/canonical_induction_circuit_v1.py")
assert SPEC and SPEC.loader
ind = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(ind)
CFG = json.loads((ROOT / "configs/canonical_induction_circuit_v1/run.json").read_text())


def test_generator_balance_uniqueness_and_disjointness() -> None:
    dev, con = ind.generate_rows(CFG, "development"), ind.generate_rows(CFG, "confirmation")
    assert len(dev) == len(con) == 128
    assert {sum(row["block_index"] == block for row in dev) for block in range(8)} == {16}
    for rows in (dev, con):
        for row in rows:
            assert len(row["clean_ids"]) == len(row["corrupt_ids"]) == len(row["sham_ids"]) == 31
            sequence = row["clean_ids"][:16]
            assert len(set(sequence + [row["contrast_id"], row["sham_id"]])) == 18
            assert row["clean_ids"][16:] == sequence[:-1]
            assert row["corrupt_ids"][15] == row["contrast_id"]
            assert row["sham_ids"][15] == row["sham_id"]
    dev_tokens = {token for row in dev for token in row["clean_ids"] + row["corrupt_ids"] + row["sham_ids"]}
    con_tokens = {token for row in con for token in row["clean_ids"] + row["corrupt_ids"] + row["sham_ids"]}
    assert not dev_tokens & con_tokens


def test_prespecified_heads_and_scope() -> None:
    assert CFG["model"]["known_heads"] == [[5, 5], [6, 9]]
    assert CFG["model"]["matched_control_heads"] == [[5, 0], [6, 0]]
    assert CFG["scope"]["technical_positive_control_only"] is True
    assert CFG["scope"]["minimum_families_for_any_future_general_claim"] == 2
    assert all(CFG["scope"][key] is False for key in ("general_method_claim", "representation_methods", "training", "natural_language_prompt_endpoint", "ioi_v1_retry", "automatic_future_method_authorization"))


class FakeProj(nn.Module):
    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return value


class FakeBlock(nn.Module):
    def __init__(self) -> None:
        super().__init__(); self.attn = SimpleNamespace(c_proj=FakeProj())


class FakeModel(nn.Module):
    def __init__(self) -> None:
        super().__init__(); self.dummy = nn.Parameter(torch.zeros(())); self.transformer = SimpleNamespace(h=nn.ModuleList([FakeBlock(), FakeBlock()]))

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, use_cache: bool, output_attentions: bool) -> SimpleNamespace:
        del attention_mask, use_cache, output_attentions
        hidden = torch.nn.functional.one_hot(input_ids % 8, num_classes=8).float()
        attentions = []
        for block in self.transformer.h:
            hidden = block.attn.c_proj(hidden)
            batch, length = input_ids.shape
            att = torch.zeros((batch, 4, length, length), dtype=torch.float32)
            att[:, :, :, 1] = 0.5
            attentions.append(att)
        return SimpleNamespace(logits=hidden, attentions=attentions)


def tiny_cfg() -> dict:
    cfg = json.loads(json.dumps(CFG)); cfg["model"].update({"batch_size": 2, "head_size": 2, "hidden_size": 8, "known_heads": [[0, 1]], "matched_control_heads": [[0, 0]]})
    return cfg


def test_head_capture_zero_and_replacement_are_exact() -> None:
    cfg = tiny_cfg(); rows = [
        {"clean_ids": [1, 2, 3], "query_position": 2, "induction_source_position": 1, "target_id": 3, "contrast_id": 4},
        {"clean_ids": [2, 3, 4], "query_position": 2, "induction_source_position": 1, "target_id": 4, "contrast_id": 5},
    ]
    model = FakeModel(); base = ind.run_condition(model, cfg, rows, "clean", [[0, 1]])
    assert np.array_equal(base["head_outputs"]["0.1"], np.asarray([[0, 1], [0, 0]], np.float32))
    zero = ind.run_condition(model, cfg, rows, "clean", [], zero_heads=[[0, 1]])
    assert np.array_equal(zero["logits"][:, 2:4], np.zeros((2, 2), np.float32))
    donor = {"0.1": np.asarray([[5, 6], [7, 8]], np.float32)}
    patched = ind.run_condition(model, cfg, rows, "clean", [], replacement=donor)
    assert np.array_equal(patched["logits"][:, 2:4], donor["0.1"])
    assert np.array_equal(patched["logits"][:, :2], base["logits"][:, :2])


def test_metric_oracle() -> None:
    cfg = tiny_cfg(); rows = [{"stage": "development", "row_index": 0, "block_index": 0, "component_id": "x", "target_id": 0, "contrast_id": 1}]
    def logits(margin: float) -> np.ndarray: return np.asarray([[margin, 0.0]])
    outputs = {
        "clean": {"logits": logits(2.0), "attention": {"0.1": np.asarray([0.8]), "0.0": np.asarray([0.1])}},
        "corrupt": {"logits": logits(-2.0)}, "known_zero": {"logits": logits(1.0)}, "control_zero": {"logits": logits(1.9)},
        "patched_clean": {"logits": logits(1.0)}, "patched_sham": {"logits": logits(-1.5)},
    }
    metric = ind.compute_metrics(cfg, rows, outputs)[0]
    assert metric["informative"] is True
    assert metric["attention_margin"] == pytest.approx(0.7)
    assert metric["necessity_margin"] == pytest.approx(0.9)
    assert metric["recovery"] == pytest.approx(0.75)
    assert metric["sham_recovery"] == pytest.approx(0.125)
    assert metric["selectivity"] == pytest.approx(0.625)


def test_behavior_effect_floor_is_strict() -> None:
    cfg = tiny_cfg(); rows = [{"stage": "development", "row_index": 0, "block_index": 0, "component_id": "x", "target_id": 0, "contrast_id": 1}]
    floor = cfg["gate"]["behavior_effect_floor_strict"]
    def logits(value: float) -> np.ndarray: return np.asarray([[value, 0.0]])
    outputs = {
        "clean": {"logits": logits(floor), "attention": {"0.1": np.asarray([0.8]), "0.0": np.asarray([0.1])}},
        "corrupt": {"logits": logits(-floor)}, "known_zero": {"logits": logits(0.0)}, "control_zero": {"logits": logits(0.0)},
        "patched_clean": {"logits": logits(0.0)}, "patched_sham": {"logits": logits(0.0)},
    }
    assert ind.compute_metrics(cfg, rows, outputs)[0]["informative"] is False


def good_metric_rows() -> list[dict]:
    return [{"block_index": block, "informative": True, "attention_known": 0.8, "attention_margin": 0.7, "necessity_known": 1.0, "necessity_margin": 0.9, "recovery": 0.75, "selectivity": 0.6} for block in range(8) for _ in range(16)]


def test_gate_passes_oracle() -> None:
    assert ind.summarize(CFG, good_metric_rows(), "development")["pass"] is True


@pytest.mark.parametrize(
    ("metric", "part", "config_key"),
    [
        ("attention_known", "point", "attention_known_point_min_inclusive"),
        ("attention_known", "lower", "attention_known_lower_strict"),
        ("attention_margin", "point", "attention_margin_point_min_inclusive"),
        ("attention_margin", "lower", "attention_margin_lower_strict"),
        ("necessity_known", "point", "necessity_known_point_min_inclusive"),
        ("necessity_margin", "point", "necessity_margin_point_min_inclusive"),
        ("necessity_margin", "lower", "necessity_margin_lower_strict"),
        ("recovery", "point", "sufficiency_recovery_point_min_inclusive"),
        ("recovery", "lower", "sufficiency_recovery_lower_strict"),
        ("selectivity", "point", "selectivity_point_min_inclusive"),
        ("selectivity", "lower", "selectivity_lower_strict"),
    ],
)
def test_each_registered_metric_threshold_is_enforced(monkeypatch: pytest.MonkeyPatch, metric: str, part: str, config_key: str) -> None:
    base = {name: {"point": 1.0, "lower": 0.9, "upper": 1.1, "draws": 500, "weighting": "equal_block"} for name in ("attention_known", "attention_margin", "necessity_known", "necessity_margin", "recovery", "selectivity")}
    boundary = float(CFG["gate"][config_key])
    base[metric][part] = boundary if part == "lower" else boundary - 1e-9
    monkeypatch.setattr(ind, "interval", lambda _rows, field, _draws, _seed: dict(base[field]))
    assert ind.summarize(CFG, good_metric_rows(), "development")["pass"] is False


def test_each_registered_support_threshold_is_enforced() -> None:
    rows = good_metric_rows()
    below_per_block = [row for index, row in enumerate(rows) if row["block_index"] != 0 or index < CFG["gate"]["minimum_informative_per_block"] - 1]
    assert ind.summarize(CFG, below_per_block, "development")["pass"] is False
    below_total = rows[: CFG["gate"]["minimum_informative_total"] - 1]
    assert ind.summarize(CFG, below_total, "development")["pass"] is False


def test_hierarchical_interval_is_deterministic() -> None:
    rows = good_metric_rows()
    assert ind.interval(rows, "recovery", 50, 7) == ind.interval(rows, "recovery", 50, 7)


def test_interval_uses_equal_block_estimand_with_unequal_support() -> None:
    rows = [
        {"block_index": 0, "informative": True, "x": 0.0},
        {"block_index": 1, "informative": True, "x": 10.0},
        {"block_index": 1, "informative": True, "x": 10.0},
        {"block_index": 1, "informative": True, "x": 10.0},
    ]
    result = ind.interval(rows, "x", 50, 7)
    assert result is not None and result["point"] == pytest.approx(5.0)
    assert result["weighting"] == "equal_block"


def test_repeated_inference_qa_failure_stops_before_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}
    def fake(*args: object, **kwargs: object) -> dict:
        calls["n"] += 1; value = float(calls["n"])
        return {"logits": np.full((1, 2), value), "head_outputs": {"5.5": np.full((1, 1), value), "6.9": np.full((1, 1), value)}, "attention": {}}
    monkeypatch.setattr(ind, "run_condition", fake)
    with pytest.raises(RuntimeError, match="repeated live inference QA failed"):
        ind.run_stage(CFG, object(), [{"clean_ids": [1]}])
    assert calls["n"] == 2


def test_terminal_waiter_failure_timeout_and_success(tmp_path: Path) -> None:
    failed = tmp_path / "failed"; failed.mkdir(); ind.exjson(failed / "FAILED.json", {"error": "x"})
    with pytest.raises(RuntimeError): ind.wait_for_terminals([failed], ["COMPLETE.json"], 0, 0)
    silent = tmp_path / "silent"; silent.mkdir()
    with pytest.raises(TimeoutError): ind.wait_for_terminals([silent], ["COMPLETE.json"], 0, 0)
    done = tmp_path / "done"; done.mkdir(); ind.exjson(done / "COMPLETE.json", {})
    assert ind.wait_for_terminals([done], ["COMPLETE.json"], 0, 0)[done].name == "COMPLETE.json"


def lineage_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict, Path, dict, Path]:
    monkeypatch.setattr(ind, "ROOT", tmp_path)
    cfg = json.loads(json.dumps(CFG))
    cfg["runtime"].update({"freeze": "freeze.json", "output_root": "out"})
    freeze_path = tmp_path / "freeze.json"; ind.exjson(freeze_path, {"frozen": True})
    freeze_record = {"candidate_inventory_sha256": "inventory"}
    output = tmp_path / "out"; dev = output / "development"; dev.mkdir(parents=True)
    ind.writejl(dev / "metrics.jsonl", good_metric_rows()); ind.exjson(dev / "QA.json", {"pass": True})
    ind.exjson(dev / "COMPLETE.json", {
        "schema_version": "canonical_induction_circuit_v1_complete", "stage": "development", "rows": 128,
        "freeze_sha256": ind.sha(freeze_path), "freeze_inventory_sha256": "inventory",
        "representation_methods": False, "training": False,
        "metrics_sha256": ind.sha(dev / "metrics.jsonl"), "qa_sha256": ind.sha(dev / "QA.json"),
    })
    summary = ind.summarize(cfg, ind.readjl(dev / "metrics.jsonl"), "development")
    gate_path = output / "development_gate/result.json"
    ind.exjson(gate_path, {
        "schema_version": "canonical_induction_circuit_v1_development_gate", "status": "PASS",
        "summary": summary, "confirmation_authorized": True, "technical_positive_control_only": True,
        "general_method_claim_authorized": False, "representation_methods_authorized": False,
        "training_authorized": False, "freeze_sha256": ind.sha(freeze_path),
        "freeze_inventory_sha256": "inventory",
    })
    config = tmp_path / "config.json"; config.write_text(json.dumps(cfg))
    return cfg, output, freeze_record, config


def test_development_gate_recomputes_and_binds_lineage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, output, freeze_record, _config = lineage_fixture(tmp_path, monkeypatch)
    assert ind.validate_development_gate(cfg, output, freeze_record)["confirmation_authorized"] is True
    path = output / "development_gate/result.json"; original = ind.loadj(path)
    for mutate in (
        lambda value: value.update(schema_version="wrong"),
        lambda value: value.update(freeze_inventory_sha256="wrong"),
        lambda value: value["summary"].update(informative_total=127),
        lambda value: value.update(confirmation_authorized=False),
    ):
        changed = json.loads(json.dumps(original)); mutate(changed); path.write_text(json.dumps(changed))
        with pytest.raises(RuntimeError, match="development gate lineage"):
            ind.validate_development_gate(cfg, output, freeze_record)
    path.write_text(json.dumps(original))
    metrics = output / "development/metrics.jsonl"; metrics.write_text(metrics.read_text() + "\n")
    with pytest.raises(RuntimeError, match="completion lineage"):
        ind.validate_development_gate(cfg, output, freeze_record)


def test_confirmation_invalid_gate_fails_before_payload_or_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, _output, freeze_record, config = lineage_fixture(tmp_path, monkeypatch)
    calls = {"verify_full": 0, "load": 0, "read": 0}
    def fake_verify(_config: Path, _cfg: dict, include_confirmation: bool) -> dict:
        calls["verify_full"] += int(include_confirmation); return freeze_record
    monkeypatch.setattr(ind, "verify_freeze", fake_verify)
    monkeypatch.setattr(ind, "wait_for_terminals", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(ind, "validate_development_gate", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad gate")))
    monkeypatch.setattr(ind, "load_model", lambda *_args, **_kwargs: calls.__setitem__("load", calls["load"] + 1))
    monkeypatch.setattr(ind, "readjl", lambda *_args, **_kwargs: calls.__setitem__("read", calls["read"] + 1))
    with pytest.raises(RuntimeError, match="bad gate"):
        ind.worker(config, "confirmation")
    assert calls == {"verify_full": 0, "load": 0, "read": 0}
    assert (tmp_path / "out/confirmation/FAILED.json").is_file()


def test_confirmation_stop_gate_blocks_before_payload_or_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, output, freeze_record, config = lineage_fixture(tmp_path, monkeypatch)
    calls = {"verify_full": 0, "load": 0, "read": 0}
    def fake_verify(_config: Path, _cfg: dict, include_confirmation: bool) -> dict:
        calls["verify_full"] += int(include_confirmation); return freeze_record
    monkeypatch.setattr(ind, "verify_freeze", fake_verify)
    monkeypatch.setattr(ind, "wait_for_terminals", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(ind, "validate_development_gate", lambda *_args, **_kwargs: {"confirmation_authorized": False})
    monkeypatch.setattr(ind, "load_model", lambda *_args, **_kwargs: calls.__setitem__("load", calls["load"] + 1))
    monkeypatch.setattr(ind, "readjl", lambda *_args, **_kwargs: calls.__setitem__("read", calls["read"] + 1))
    ind.worker(config, "confirmation")
    assert calls == {"verify_full": 0, "load": 0, "read": 0}
    blocked = ind.loadj(output / "confirmation/BLOCKED.json")
    assert blocked["model_loaded"] is False and blocked["confirmation_rows_loaded"] is False
    assert blocked["development_gate_sha256"] == ind.sha(output / "development_gate/result.json")


def test_pre_gate_preflight_excludes_confirmation_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[bool] = []
    monkeypatch.setattr(ind, "preservation_verify", lambda _cfg: None)
    monkeypatch.setattr(ind, "verify_prepared", lambda _cfg, include_confirmation=True: seen.append(include_confirmation))
    ind.preflight(ROOT / "configs/canonical_induction_circuit_v1/run.json", include_confirmation=False)
    assert seen == [False]


def test_review_binding_cannot_be_bypassed_by_python_optimization(tmp_path: Path) -> None:
    freeze = tmp_path / "FREEZE.json"; freeze.write_text("{}\n")
    candidate = tmp_path / "candidate.md"; candidate.write_text("VERDICT: SHIP\n")
    frozen = tmp_path / "frozen.md"; frozen.write_text("VERDICT: SHIP\n")
    binding = tmp_path / "binding.json"
    binding.write_text(json.dumps({
        "status": "SHIP", "candidate_verdict": "SHIP", "frozen_verdict": "SHIP",
        "freeze_sha256": ind.sha(freeze), "candidate_review_sha256": ind.sha(candidate),
        "frozen_review_sha256": "deliberately-wrong",
    }))
    code = (
        "import importlib.util,pathlib,sys;"
        "s=importlib.util.spec_from_file_location('ind',sys.argv[1]);"
        "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        "m.validate_review_binding(*map(pathlib.Path,sys.argv[2:]))"
    )
    result = subprocess.run([sys.executable, "-O", "-c", code, str(ROOT / "scripts/canonical_induction_circuit_v1.py"), str(freeze), str(candidate), str(frozen), str(binding)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "review binding mismatch" in result.stderr


def test_ioi_preservation_rejects_extra_file_in_closed_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest_source = ROOT / CFG["preservation"]["ioi_v1_manifest"]
    manifest = json.loads(manifest_source.read_text())
    for record in manifest["files"]:
        source = ROOT / record["path"]; target = tmp_path / record["path"]
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    target_manifest = tmp_path / CFG["preservation"]["ioi_v1_manifest"]
    target_manifest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(manifest_source, target_manifest)
    original_freeze = json.loads((ROOT / "configs/known_mechanism_ioi_v1/FREEZE.json").read_text())
    migrated = {"PAPER.md", "reports/paper_claim_ledger_v1.json"}
    for record in original_freeze["candidate_inventory"]:
        if record["path"] in migrated:
            continue
        source = ROOT / record["path"]; target = tmp_path / record["path"]
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
    cfg = json.loads(json.dumps(CFG)); cfg["preservation"]["ioi_v1_manifest_sha256"] = ind.sha(target_manifest)
    monkeypatch.setattr(ind, "ROOT", tmp_path)
    ind.preservation_verify(cfg)
    omitted = tmp_path / "scripts/known_mechanism_ioi_v1.py"; original = omitted.read_bytes(); omitted.write_bytes(original + b"\n# drift\n")
    with pytest.raises(RuntimeError, match="original frozen input drift"):
        ind.preservation_verify(cfg)
    omitted.write_bytes(original)
    extra = tmp_path / manifest["tree_roots"][1] / "UNREGISTERED.txt"; extra.write_text("drift")
    with pytest.raises(RuntimeError, match="tree inventory drift"):
        ind.preservation_verify(cfg)


def test_create_once_namespace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "once.json"; ind.exjson(path, {"value": 1})
    with pytest.raises(FileExistsError): ind.exjson(path, {"value": 2})
    monkeypatch.setattr(ind, "ROOT", tmp_path)
    cfg = json.loads(json.dumps(CFG)); cfg["runtime"]["output_root"] = "existing"; config = tmp_path / "config.json"; config.write_text(json.dumps(cfg))
    (tmp_path / "existing/development").mkdir(parents=True)
    monkeypatch.setattr(ind, "verify_freeze", lambda *_args, **_kwargs: {"candidate_inventory_sha256": "x"})
    with pytest.raises(FileExistsError): ind.worker(config, "development")
    launcher = (ROOT / "scripts/launch_canonical_induction_circuit_v1_tmux.sh").read_text()
    assert "CUBLAS_WORKSPACE_CONFIG=:4096:8" in launcher
    assert "CUDA_VISIBLE_DEVICES='$uuid'" in launcher and "EXPECTED_GPU_UUID='$uuid'" in launcher
    assert '$(head -n 1 "$CANDIDATE")' in launcher and '$(head -n 1 "$FROZEN")' in launcher
    assert "grep -q '^VERDICT: SHIP$'" not in launcher
    assert "preflight --pre-gate --config" in launcher and "verify-freeze --pre-gate --config" in launcher
    assert '"$PY" "$RUN" review-binding --config "$CONFIG"' in launcher
    assert "assert actual" not in launcher
    assert "method-worker" not in launcher and "train" not in launcher.lower()
