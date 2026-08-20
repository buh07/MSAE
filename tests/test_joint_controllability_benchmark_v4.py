import json
import threading
from pathlib import Path

import numpy as np
import pytest

import joint_controllability_benchmark_v4 as v4


def test_native_json_converts_numpy_boolean():
    assert v4.native({"passes": np.bool_(False)}) == {"passes": False}
    json.dumps(v4.native({"passes": np.bool_(False)}))


def test_development_gate_requires_effect_and_low_sham():
    gate = {"minimum_full_effect": 0.25, "minimum_effect_eligibility": 0.85, "minimum_eligible_rows": 17, "maximum_sham_fraction": 0.20, "maximum_sham_fraction_ci": 0.30, "bootstrap_draws": 100, "epsilon": 1e-8}
    good = [{"full_effect": 1.0, "sham_effect": 0.05, "component_block": str(i)} for i in range(20)]
    assert v4.development_gate_summary(good, gate, 1)["passes"] is True
    high_sham = [{**row, "sham_effect": 0.5} for row in good]
    assert v4.development_gate_summary(high_sham, gate, 1)["passes"] is False
    weak = [{**row, "full_effect": 0.1} for row in good]
    assert v4.development_gate_summary(weak, gate, 1)["passes"] is False


def test_ineligible_near_zero_rows_do_not_enter_sham_ratio():
    gate = {"minimum_full_effect": 0.25, "minimum_effect_eligibility": 0.85, "minimum_eligible_rows": 17, "maximum_sham_fraction": 0.20, "maximum_sham_fraction_ci": 0.30, "bootstrap_draws": 100, "epsilon": 1e-8}
    rows = [{"full_effect": 1.0, "sham_effect": 0.05, "component_block": str(i)} for i in range(17)]
    rows += [{"full_effect": 0.0, "sham_effect": 100.0, "component_block": "bad0"}, {"full_effect": 1e-15, "sham_effect": 100.0, "component_block": "bad1"}, {"full_effect": -1.0, "sham_effect": 100.0, "component_block": "bad2"}]
    got = v4.development_gate_summary(rows, gate, 2)
    assert got["passes"] is True
    assert got["eligible_rows"] == 17


def test_v4_has_no_training_entry_point():
    text = Path(v4.__file__).read_text().lower()
    forbidden = ["optimizer", ".backward(", "train_msae", "train_k2", "sae_training_authorized\": true"]
    assert not any(term in text for term in forbidden)


def test_worker_waits_before_model_loading():
    text = Path(v4.__file__).read_text()
    body = text[text.index("def _worker(") : text.index("def worker(")]
    assert body.index("wait_gates(cfg, out)") < body.index("from transformers import AutoModelForCausalLM")


def test_excluded_documents_include_all_v3_roles():
    cfg = json.loads(v4.DEFAULT.read_text())
    excluded = v4.excluded_v3_documents(cfg)
    rows = v4.readjl(v4.ROOT / cfg["task"]["exclude_v3_rows"])
    assert len(excluded) == 3 * len(rows)


def test_prepared_rows_are_exactly_matched_disjoint_and_deterministic():
    cfg = json.loads(v4.DEFAULT.read_text()); root = v4.ROOT / cfg["runtime"]["prepared_root"]
    manifest = json.loads((root / "PRESCORE.json").read_text())
    assert manifest["rows"] == manifest["unique_documents"] == 384
    assert manifest["development_test_disjoint"] and manifest["v3_document_overlap"] == 0
    attestation = json.loads((v4.ROOT / "reports/provenance/joint_controllability_benchmark_v4/deterministic_prepare.json").read_text())
    assert attestation["status"] == "PASS" and attestation["runs"] == 2
    for model in ("gpt2", "pythia160", "gemma2"):
        rows = v4.readjl(root / f"{model}.jsonl")
        assert len(rows) == 384
        assert all(len(r["base_prompt_ids"]) == len(r["full_prompt_ids"]) == len(r["sham_prompt_ids"]) for r in rows)
        assert v4.sha(root / f"{model}.jsonl") == attestation["reference_files"][f"{model}.jsonl"]


def test_wait_gates_stops_immediately_on_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(v4, "ROOT", tmp_path)
    cfg = {"runtime": {"output_root": "out", "freeze": "freeze.json", "gate_timeout_seconds": 1, "gate_poll_seconds": 1}}
    (tmp_path / "out/task_gate").mkdir(parents=True); (tmp_path / "out/task_gate/FAIL.json").write_text('{"status":"FAIL"}\n')
    with pytest.raises(RuntimeError, match="blocked"):
        v4.wait_gates(cfg, tmp_path / "worker")


def test_task_worker_exception_writes_failure_terminal(tmp_path: Path, monkeypatch):
    config = tmp_path / "run.json"; config.write_text(json.dumps({"runtime": {"output_root": "out", "freeze": "freeze.json"}}))
    monkeypatch.setattr(v4, "ROOT", tmp_path)
    monkeypatch.setattr(v4, "_task_gate_worker", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        v4.task_gate_worker(config, "gpt2")
    assert json.loads((tmp_path / "out/task_gate/gpt2_FAIL.json").read_text())["status"] == "FAIL"


def test_exclusive_output_and_worker_lineage_validation(tmp_path: Path):
    path = tmp_path / "exclusive.json"; v4.exjson(path, {"ok": True})
    with pytest.raises(FileExistsError): v4.exjson(path, {"ok": False})
    root = tmp_path / "run"; directory = root / "shards/gpt2_layer1"; directory.mkdir(parents=True)
    (directory / "HOOK_QA.json").write_text('{"zero_patch_exact":true}\n')
    cfg = {"methods": ["m"], "budgets": [0.25], "task": {"sources": ["A", "B"]}, "models": [{"key": "gpt2", "sae": {"format": "saelens_topk"}}]}
    prepared = [{"source": "A", "split": "test", "component_id": "a", "component_block": "ba"}, {"source": "B", "split": "test", "component_id": "b", "component_block": "bb"}]
    rows = [{"schema_version": "joint_control_v4_component_metric", "model": "gpt2", "layer": 1, "fit_source": "A", "eval_source": "B", "method": "m", "budget": 0.25, "component_id": "b", "component_block": "bb"}, {"schema_version": "joint_control_v4_component_metric", "model": "gpt2", "layer": 1, "fit_source": "B", "eval_source": "A", "method": "m", "budget": 0.25, "component_id": "a", "component_block": "ba"}]
    v4.writejl(directory / "metrics.jsonl", rows)
    complete = {"schema_version": "joint_control_v4_worker_complete", "status": "COMPLETE", "model": "gpt2", "layer": 1, "rows": 2, "freeze_sha256": "f", "hook_qa_sha256": v4.sha(directory / "HOOK_QA.json"), "metrics_sha256": v4.sha(directory / "metrics.jsonl")}
    v4.exjson(directory / "COMPLETE.json", complete)
    assert len(v4.validate_worker_artifacts(root, "gpt2_layer1", "f", cfg, prepared)[0]) == 2
    with pytest.raises(RuntimeError, match="worker drift"):
        v4.validate_worker_artifacts(root, "gpt2_layer1", "wrong", cfg, prepared)


def test_metric_grid_rejects_omission_duplicate_and_extra():
    cfg = {"methods": ["m"], "budgets": [0.25], "task": {"sources": ["A", "B"]}, "models": [{"key": "gpt2", "sae": {"format": "saelens_topk"}}]}
    prepared = [{"source": "A", "split": "test", "component_id": "a", "component_block": "ba"}, {"source": "B", "split": "test", "component_id": "b", "component_block": "bb"}]
    good = [{"fit_source": "A", "eval_source": "B", "method": "m", "budget": 0.25, "component_id": "b", "component_block": "bb"}, {"fit_source": "B", "eval_source": "A", "method": "m", "budget": 0.25, "component_id": "a", "component_block": "ba"}]
    v4.validate_metric_grid(good, cfg, prepared, "gpt2")
    for bad in (good[:1], good + [good[0]], good + [{**good[0], "component_id": "extra"}]):
        with pytest.raises(RuntimeError, match="metric grid"):
            v4.validate_metric_grid(bad, cfg, prepared, "gpt2")
    with pytest.raises(RuntimeError, match="metric grid"):
        v4.validate_metric_grid([{**good[0], "component_block": "wrong"}, good[1]], cfg, prepared, "gpt2")


def test_task_evidence_is_identical_across_methods_and_budgets():
    cfg = {"seed": 7, "analysis": {"bootstrap_draws": 50, "minimum_eligible_rows": 2, "minimum_effect_eligibility": 0.8, "maximum_sham_fraction": 0.25, "maximum_sham_fraction_ci": 0.35}}
    natural = [{"component_id": "a", "component_block": "a", "full_effect": 1.0, "natural_sham_effect": 0.05, "behavior_eligible": True}, {"component_id": "b", "component_block": "b", "full_effect": 1.0, "natural_sham_effect": 0.05, "behavior_eligible": True}]
    groups = {("m1", 0.25, "gpt2", 1, "A", "B"): natural, ("m2", 1.0, "gpt2", 1, "A", "B"): [dict(row) for row in natural]}
    evidence = v4.method_independent_task_evidence(groups, cfg)
    assert len(evidence) == 1
    changed = dict(groups); changed[("m2", 1.0, "gpt2", 1, "A", "B")] = [{**natural[0], "full_effect": 2.0}, natural[1]]
    with pytest.raises(RuntimeError, match="method-dependent"):
        v4.method_independent_task_evidence(changed, cfg)


def test_exclusive_json_is_published_only_after_complete_write(tmp_path: Path, monkeypatch):
    target = tmp_path / "terminal.json"; entered = threading.Event(); release = threading.Event(); errors = []
    original_link = v4.os.link
    def delayed_link(source, destination):
        entered.set(); release.wait(timeout=5); return original_link(source, destination)
    monkeypatch.setattr(v4.os, "link", delayed_link)
    def writer():
        try: v4.exjson(target, {"status": "COMPLETE", "payload": "x" * 10000})
        except BaseException as error: errors.append(error)
    thread = threading.Thread(target=writer); thread.start(); assert entered.wait(timeout=5)
    assert not target.exists()
    release.set(); thread.join(timeout=5)
    assert not errors and json.loads(target.read_text())["status"] == "COMPLETE"
