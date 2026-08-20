import importlib.util
import json
import math
import hashlib
import sys
from collections import Counter
from pathlib import Path

import pytest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("behavioral_endpoint_v6_2", ROOT / "scripts/behavioral_endpoint_v6_2.py")
v6 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(v6)
CFG_PATH = ROOT / "configs/behavioral_endpoint_v6_2/run.json"
CFG = json.loads(CFG_PATH.read_text())
PREP = ROOT / CFG["runtime"]["prepared_root"]


def rows(name):
    return v6.readjl(PREP / name)


def test_condition_logits_accumulates_every_batch_in_order(monkeypatch):
    torch = v6.torch
    sample = [{"row": i} for i in range(5)]

    def fake_batch_tensors(rr, kind, pad, device):
        ids = torch.tensor([[r["row"]] for r in rr], device=device)
        mask = torch.ones_like(ids)
        bounds = torch.zeros(len(rr), dtype=torch.long, device=device)
        return ids, mask, bounds, None

    class Model:
        calls = 0

        def __call__(self, input_ids, attention_mask, use_cache):
            self.calls += 1
            logits = torch.zeros((len(input_ids), 1, 3), dtype=torch.float32, device=input_ids.device)
            logits[:, 0, 0] = input_ids[:, 0]
            logits[:, 0, 1] = input_ids[:, 0] + 10
            return type("Output", (), {"logits": logits})()

    monkeypatch.setattr(v6.core, "batch_tensors", fake_batch_tensors)
    model = Model()
    got = v6.condition_logits(model, sample, "condition_0", 2, 0, torch.device("cpu"))
    assert model.calls == 3
    assert got.shape == (5, 3)
    np.testing.assert_array_equal(got[:, :2], np.asarray([[i, i + 10] for i in range(5)]))


def test_condition_logits_rejects_empty_or_invalid_batch():
    with pytest.raises(ValueError, match="nonempty"):
        v6.condition_logits(object(), [], "condition_0", 2, 0, v6.torch.device("cpu"))
    with pytest.raises(ValueError, match="positive"):
        v6.condition_logits(object(), [{"row": 0}], "condition_0", 0, 0, v6.torch.device("cpu"))


def test_merge_condition_batches_rejects_duplicate_or_missing_rows():
    good = np.asarray([[1.0], [2.0]])
    with pytest.raises(RuntimeError, match="order/coverage"):
        v6.merge_condition_batches([([0, 0], good)], 2)
    with pytest.raises(RuntimeError, match="order/coverage"):
        v6.merge_condition_batches([([0], good[:1])], 2)
    with pytest.raises(RuntimeError, match="row mismatch"):
        v6.merge_condition_batches([([0, 1], good[:1])], 2)


def test_failed_v6_1_tree_membership_rejects_added_files(tmp_path, monkeypatch):
    root = tmp_path / "old";log = root / "logs/worker.log";log.parent.mkdir(parents=True);log.write_text("failure")
    failed = {
        "tree_roots": ["old"],
        "files": [{"path": "old/logs/worker.log"}],
        "expected_terminal_counts": {
            "development_worker_failures": 0,
            "confirmation_blocks": 0,
            "development_gate_failures": 0,
            "final_failures": 0,
        },
    }
    monkeypatch.setattr(v6, "ROOT", tmp_path)
    v6.verify_failure_tree_membership(failed)
    (root / "logs/unregistered.log").write_text("drift")
    with pytest.raises(RuntimeError, match="membership drift"):
        v6.verify_failure_tree_membership(failed)


def test_v6_2_preserves_failed_v6_1_and_recursive_dependency_closure():
    prior = v6.recovery_verify(CFG_PATH, CFG)
    assert prior["schema_version"] == "behavioral_endpoint_v6_1_freeze"
    closure = {p.relative_to(ROOT).as_posix() for p in v6.local_dependency_closure([
        ROOT / "scripts/behavioral_endpoint_v6_2.py",
        ROOT / "scripts/behavioral_endpoint_v6_1.py",
        ROOT / "scripts/joint_controllability_benchmark_v3.py",
        ROOT / "scripts/joint_controllability_assay_v5.py",
    ])}
    required = {
        "scripts/behavioral_endpoint_v6_1.py",
        "scripts/behavioral_endpoint_v6_2.py",
        "scripts/joint_controllability_assay_v5.py",
        "scripts/joint_controllability_benchmark_v3.py",
        "scripts/joint_controllability_benchmark_v4_1.py",
        "scripts/proxy_control_benchmark_v1.py",
        "scripts/proxy_control_benchmark_v2.py",
    }
    assert required <= closure
    assert set(CFG["recovery"]["required_dependency_closure"]) <= closure
    assert CFG["recovery"]["scientific_protocol_changed"] is False
    assert CFG["recovery"]["new_model_forwards_after_v6_1_terminal"] is False
    failure = json.loads((ROOT / CFG["recovery"]["failed_v6_1_preservation"]).read_text())
    assert failure["status"] == "PRESERVED_TECHNICAL_FAILURE"
    assert failure["formal_scientific_result"] is False
    assert failure["development_workers_failed"] == 6


def test_v5_is_hash_preserved_and_confirmation_stays_sealed():
    v6.preservation_verify(CFG)
    manifest = json.loads((ROOT / CFG["preservation"]["v5_manifest"]).read_text())
    freeze = json.loads((ROOT / CFG["preservation"]["v5_freeze"]).read_text())
    assert {x["path"] for x in freeze["candidate_inventory"]} <= {x["path"] for x in manifest["files"]}
    assert CFG["preservation"]["training_authorized"] is False
    assert CFG["preservation"]["representation_methods_authorized"] is False
    assert CFG["preservation"]["v5_confirmation_open_authorized"] is False


def test_v5_report_is_analysis_only_and_binds_inputs():
    p = ROOT / CFG["preservation"]["v5_analysis"]
    report = json.loads(p.read_text())
    assert report["analysis_only"] and not report["new_model_forwards"]
    assert not report["v5_rescored"] and report["formal_v5_status"] == "FAIL"
    assert len(report["cells"]) == 18 and report["key_answer_strata"]
    assert len([x for x in report["inputs"] if x.endswith("/COMPLETE.json")]) == 3
    for name, digest in report["inputs"].items():
        assert v6.sha(ROOT / name) == digest


def test_prescore_grid_sources_and_development_confirmation_disjointness():
    prescore = json.loads((PREP / "PRESCORE.json").read_text())
    assert prescore["selection_firewall"] == "LABEL_TOKENIZER_ONLY_NO_MODEL_FORWARD"
    assert prescore["rows"] == {"agreement": 1152, "retrieval": 1152}
    assert prescore["confirmation_documents"] == 384
    assert all(x["full_rank"] for x in prescore["agreement_design"].values())
    assert prescore["agreement_design"]["development"]["rank"] == prescore["agreement_design"]["development"]["columns"]
    dev = rows("V5_DEVELOPMENT_PROJECTION.jsonl")
    conf = rows("CONFIRMATION_DOCUMENTS.jsonl")
    assert len(dev) == len(conf) == 384
    assert {x["document_id"] for x in dev}.isdisjoint({x["document_id"] for x in conf})
    assert {x["content_hash"] for x in dev}.isdisjoint({x["content_hash"] for x in conf})
    assert {x["window_hash"] for x in dev}.isdisjoint({x["window_hash"] for x in conf})
    predecessor, audit = v6.predecessor_exclusions(CFG)
    assert len(audit) == 2 and all(x["rows"] == 384 for x in audit)
    assert {x["document_id"] for x in conf}.isdisjoint(predecessor["document_id"])
    assert {x["content_hash"] for x in conf}.isdisjoint(predecessor["content_hash"])
    assert {x["window_hash"] for x in conf}.isdisjoint(predecessor["window_hash"])
    expected_rejections = sum(x["rejected_records"] for x in prescore["confirmation_selection"])
    assert expected_rejections == sum(x["dataset_rows"] - x["accepted"] for x in prescore["confirmation_selection"])
    with (PREP / "CONFIRMATION_REJECTIONS.jsonl").open("rb") as f:
        assert sum(block.count(b"\n") for block in iter(lambda: f.read(8 << 20), b"")) == expected_rejections
    assert prescore["source_fingerprints"] == {
        "DBPEDIA_CONFIRMATION": "beedf461d6a52841",
        "IMDB_CONFIRMATION": "b22c1504b46f1653",
    }


def test_v5_projection_is_binary_streamed_without_whole_file_reads(monkeypatch):
    original = Path.read_bytes
    sealed = {str(ROOT / CFG["panel"]["v5_rows"]), str(ROOT / CFG["panel"]["v5_accepted"])}
    def guarded(path):
        if str(path) in sealed:
            raise AssertionError("sealed V5 file was read wholesale")
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", guarded)
    dev, hashes = v6.development_projection(CFG)
    assert len(dev) == 384 and all(len(x) == 384 for x in hashes.values())


@pytest.mark.parametrize("endpoint", ["retrieval", "agreement"])
def test_exact_panel_counts_and_document_blocking(endpoint):
    rr = rows(f"{endpoint}_rows.jsonl")
    counts = Counter((r["stage"], r["source"], int(r["template_index"])) for r in rr)
    assert set(counts.values()) == {64}
    assert len(counts) == 18
    for stage, templates in (("development", 6), ("confirmation", 3)):
        rstage = [r for r in rr if r["stage"] == stage]
        expected_sources = CFG["panel"][f"{stage}_sources"]
        assert len(rstage) == len(expected_sources) * templates * 64
        for source in expected_sources:
            src = [r for r in rstage if r["source"] == source]
            assert len({r["component_block"] for r in src}) == 192


def test_retrieval_conditions_are_complete_and_shams_hold_target_binding():
    rr = rows("retrieval_rows.jsonl")
    for r in rr:
        assert r["condition_names"] == ["match", "counterfactual_0", "counterfactual_1", "counterfactual_2", "sham_1", "sham_2", "no_binding"] or (
            r["condition_names"][0] == "match"
            and r["condition_names"][-3:] == ["sham_1", "sham_2", "no_binding"]
            and len([x for x in r["condition_names"] if x.startswith("counterfactual_")]) == 3
        )
        assert len(r["condition_tables"]) == len(r["condition_prompts"]) == 7
        assert len(r["correct_candidate_indices"]) == 7
        q, v = int(r["query_index"]), int(r["value_index"])
        for i in (0, 4, 5):
            assert f"{r['keys'][q]}={r['candidate_words'][v]}" in r["condition_tables"][i]
        assert r["correct_candidate_indices"][0] == v
        assert r["correct_candidate_indices"][-1] == 4
        n = CFG["retrieval"][f"{r['stage']}_no_binding_scaffold_words"][int(r["template_index"])]
        assert r["condition_tables"][-1] == " ".join(["unavailable"] * n)
        forbidden = {x.lower() for ks in CFG["retrieval"][f"{r['stage']}_key_sets"] for x in ks} | {x.lower() for x in r["candidate_words"]}
        _, leaks = v6.sanitize_retrieval_filler(r["condition_prompts"][-1], forbidden)
        assert leaks == 0
        assert r["query_key"] not in r["condition_prompts"][-1].split()


def test_agreement_counterfactuals_and_balanced_assignments():
    rr = rows("agreement_rows.jsonl")
    assert all(r["condition_names"] == ["original", "subject_flip", "attractor_flip", "lexical_sham"] for r in rr)
    assert all(len(r["condition_prompts"]) == len(r["condition_surfaces"]) == 4 for r in rr)
    for r in rr:
        s = r["condition_surfaces"]
        assert s[0][0] != s[1][0] and s[0][1] == s[1][1]
        assert s[0][0] == s[2][0] and s[0][1] != s[2][1]
        assert s[0] != s[3]
    for key, group in _groups(rr, lambda r: (r["stage"], r["source"], r["template_index"], r["set_index"])).items():
        assert len(group) == 16, key
        for field in ("subject_lemma_index", "attractor_lemma_index", "lexical_subject_index", "lexical_attractor_index", "verb_pair_index"):
            assert Counter(int(r[field]) for r in group) == Counter({0: 4, 1: 4, 2: 4, 3: 4}), (key, field)
        assert Counter(int(r["subject_number"]) for r in group) == Counter({0: 8, 1: 8})
        assert Counter(int(r["attractor_number"]) for r in group) == Counter({0: 8, 1: 8})
    for stage in ("development", "confirmation"):
        stage_rows = [r for r in rr if r["stage"] == stage]
        for field in ("subject_lemma_index", "subject_number", "attractor_number"):
            for value in sorted({int(r[field]) for r in stage_rows}):
                counts = Counter(int(r["verb_pair_index"]) for r in stage_rows if int(r[field]) == value)
                assert len(counts) == 4 and len(set(counts.values())) == 1, (stage, field, value, counts)


def _groups(items, key):
    out = {}
    for item in items:
        out.setdefault(key(item), []).append(item)
    return out


@pytest.mark.parametrize("endpoint,ncond", [("retrieval", 7), ("agreement", 4)])
def test_tokenizer_length_and_single_token_candidate_gates(endpoint, ncond):
    for model in ("gpt2", "pythia160", "gemma2"):
        rr = rows(f"{endpoint}_{model}.jsonl")
        assert len(rr) == 1152
        for r in rr:
            lengths = {len(r[f"condition_{i}_prompt_ids"]) for i in range(ncond)}
            assert len(lengths) == 1
            assert max(lengths) + 1 <= CFG["runtime"]["maximum_length"]
            if endpoint == "retrieval":
                assert len(r["candidate_ids"]) == 5 == len(set(r["candidate_ids"]))
            else:
                assert len(r["continuation_ids"]) == 1 and r["target_id"] != r["contrast_id"]


def _metric_rows(ratio=0.1, eligible_per_set=16):
    out = []
    for s in range(4):
        for i in range(16):
            eligible = i < eligible_per_set
            out.append({"set_index": s, "eligible": eligible, "ratio": ratio if eligible else None, "component_block": f"s{s}:i{i}"})
    return out


def test_frozen_cell_support_and_specificity_gates(monkeypatch):
    assert v6.cell_summary(_metric_rows(), CFG, 1)["passes"]
    assert v6.cell_summary(_metric_rows(ratio=0.2), CFG, 1)["passes"]
    assert not v6.cell_summary(_metric_rows(ratio=math.nextafter(0.2, math.inf)), CFG, 1)["passes"]
    assert not v6.cell_summary(_metric_rows(eligible_per_set=13), CFG, 1)["passes"]
    assert not v6.cell_summary(_metric_rows(ratio=0.31), CFG, 1)["passes"]
    calls = []
    monkeypatch.setattr(v6, "qhigher", lambda values, q: (calls.append(q) or (0.3 if q == CFG["gate"]["quantile"] else 0.0)))
    assert not v6.cell_summary(_metric_rows(ratio=0.1), CFG, 1)["passes"]
    assert calls == [1 - CFG["gate"]["quantile"], CFG["gate"]["quantile"]]


def test_crossed_hierarchy_constant_or_sparse_oracle():
    good = []
    for t in range(6):
        for s in range(4):
            for i in range(16):
                good.append({"template_index": t, "set_index": s, "component_block": f"d{s}:{t % 3}:{i}", "eligible": True, "ratio": 0.1})
    out = v6.overall_summary(good, 6, CFG, 7)
    assert out["passes"] and out["ratio_interval"] == pytest.approx([0.1, 0.1, 0.1])
    for r in good:
        if r["template_index"] == 0 and r["set_index"] == 0:
            r["eligible"] = False
            r["ratio"] = None
    assert not v6.overall_summary(good, 6, CFG, 7)["passes"]


def test_crossed_hierarchy_uses_literal_component_product_weights(monkeypatch):
    rows = []
    for t in range(2):
        for s in range(4):
            for d in range(3):
                eligible = d == 0 or (d == 1 and (t + s) % 2 == 0) or d == 2
                rows.append({"template_index": t, "set_index": s, "component_block": f"d{d}", "eligible": eligible, "ratio": float(1 + 10*t + 2*s + d) if eligible else None})
    template_sample = np.array([0, 0]);set_sample = np.array([0, 1, 1, 2]);document_sample = np.array([0, 0, 1])
    class FakeRNG:
        def __init__(self):self.calls = iter([template_sample, set_sample, document_sample])
        def integers(self, low, high, size):
            out = next(self.calls);assert len(out) == size;return out
    monkeypatch.setattr(v6.np.random, "default_rng", lambda seed: FakeRNG())
    cfg = json.loads(json.dumps(CFG));cfg["gate"]["bootstrap_draws"] = 1
    tm, sm, dm = Counter(template_sample), Counter(set_sample), Counter(f"d{i}" for i in document_sample)
    num = den = 0.0
    for r in rows:
        w = tm[int(r["template_index"])] * sm[int(r["set_index"])] * dm[r["component_block"]]
        if w and r["eligible"]:num += w * r["ratio"];den += w
    expected = num / den
    summary = v6.overall_summary(rows, 2, cfg, 99)
    assert summary["ratio_interval"][0] == pytest.approx(expected)
    assert summary["ratio_interval"][2] == pytest.approx(expected)


def test_component_metric_oracles():
    retrieval = np.zeros((7, 5), dtype=float)
    correct = [0, 1, 2, 3, 0, 0, 4]
    for i, c in enumerate(correct):
        retrieval[i, c] = 5.0
    f, n, directional, extra = v6.component_metric("retrieval", {"correct_candidate_indices": correct, "value_index": 0}, retrieval)
    assert directional and f > 4 and n == pytest.approx(0.0)
    assert len(extra["top1_margins"]) == 7
    f, n, directional, _ = v6.component_metric("agreement", {}, np.array([2.0, -2.0, 1.9, 2.1]))
    assert directional and f == pytest.approx(4.0) and n == pytest.approx(0.1)


def test_upper_higher_quantile_zero_outlier_boundary():
    assert math.isfinite(v6.qhigher([0.0] * 488 + [math.inf] * 12, 0.975))
    assert math.isinf(v6.qhigher([0.0] * 487 + [math.inf] * 13, 0.975))


def test_confirmation_authorization_is_endpoint_and_model_specific():
    gate = {"status": "PASS", "models": [
        {"model": "gpt2", "eligible_all_sources_templates": True},
        {"model": "pythia160", "eligible_all_sources_templates": False},
    ]}
    assert v6.endpoint_authorized(gate, "gpt2")
    assert not v6.endpoint_authorized(gate, "pythia160")
    assert not v6.endpoint_authorized({**gate, "status": "FAIL"}, "gpt2")


def test_registered_outcome_classifications_and_final_matrix():
    assert v6.development_classification(2, True, 2) == ("PASS", "PASS")
    assert v6.development_classification(1, True, 2) == ("FAIL", "INSUFFICIENT_MODEL_REPLICATION")
    assert v6.development_classification(0, True, 2) == ("FAIL", "TEMPLATE_CONDITIONED")
    assert v6.development_classification(0, False, 2) == ("FAIL", "FAIL")
    assert v6.final_decision(["retrieval"], ["retrieval"]) == "RETRIEVAL_CONFIRMED"
    assert v6.final_decision(["agreement"], ["agreement"]) == "AGREEMENT_CONFIRMED"
    assert v6.final_decision(["retrieval", "agreement"], ["retrieval", "agreement"]) == "BOTH_CONFIRMED"
    assert v6.final_decision([], []) == "BOTH_ENDPOINTS_STOP"
    assert v6.final_decision([], ["retrieval"]) == "STOP_NATURALISTIC_CONTROL"


def test_confirmation_worker_does_not_score_ineligible_model(tmp_path, monkeypatch):
    cfg = json.loads(json.dumps(CFG))
    cfg["runtime"]["output_root"] = "out"
    cfg["runtime"]["freeze"] = "freeze.json"
    (tmp_path / "freeze.json").write_text("{}")
    gp = tmp_path / "out/development_gate/retrieval"
    gp.mkdir(parents=True)
    (gp / "result.json").write_text(json.dumps({"status": "PASS", "models": [{"model": "gpt2", "eligible_all_sources_templates": False}]}))
    monkeypatch.setattr(v6, "ROOT", tmp_path)
    monkeypatch.setattr(v6, "loadj", lambda p: cfg if Path(p).name == "config.json" else json.loads(Path(p).read_text()))
    monkeypatch.setattr(v6, "verify_freeze", lambda *args: {})
    called = []
    monkeypatch.setattr(v6, "score", lambda *args: called.append(True))
    v6.worker(tmp_path / "config.json", "retrieval", "gpt2", "confirmation")
    assert not called
    blocked = json.loads((tmp_path / "out/confirmation/retrieval/gpt2/BLOCKED.json").read_text())
    assert blocked["model_loaded"] is False


def test_timeout_terminal_and_waiter_timeout(tmp_path, monkeypatch):
    cfg = json.loads(json.dumps(CFG));cfg["runtime"]["output_root"] = "out";cfg["runtime"]["freeze"] = "freeze.json";cfg["runtime"]["gate_timeout_seconds"] = 0
    (tmp_path / "freeze.json").write_text("{}")
    monkeypatch.setattr(v6, "ROOT", tmp_path)
    monkeypatch.setattr(v6, "loadj", lambda p: cfg if Path(p).name == "config.json" else json.loads(Path(p).read_text()))
    monkeypatch.setattr(v6, "verify_freeze", lambda *args: {})
    with pytest.raises(TimeoutError):v6.worker(tmp_path / "config.json", "retrieval", "gpt2", "confirmation")
    term = json.loads((tmp_path / "out/confirmation/retrieval/gpt2_TIMEOUT.json").read_text())
    assert term["status"] == "TIMEOUT"
    cfg["runtime"]["worker_timeout_seconds"] = 0
    with pytest.raises(TimeoutError):v6.wait_workers(tmp_path / "none", "development", "retrieval", ["gpt2"], cfg)


def test_upstream_gate_timeout_blocks_before_score(tmp_path, monkeypatch):
    cfg = json.loads(json.dumps(CFG));cfg["runtime"]["output_root"] = "out";cfg["runtime"]["freeze"] = "freeze.json"
    (tmp_path / "freeze.json").write_text("{}");gate = tmp_path / "out/development_gate/retrieval";gate.mkdir(parents=True);(gate / "TIMEOUT.json").write_text('{"status":"TIMEOUT"}')
    monkeypatch.setattr(v6, "ROOT", tmp_path);monkeypatch.setattr(v6, "loadj", lambda p: cfg if Path(p).name == "config.json" else json.loads(Path(p).read_text()));monkeypatch.setattr(v6, "verify_freeze", lambda *args: {})
    called=[];monkeypatch.setattr(v6,"score",lambda *args:called.append(True))
    v6.worker(tmp_path / "config.json", "retrieval", "gpt2", "confirmation")
    assert not called
    assert json.loads((tmp_path / "out/confirmation/retrieval/gpt2/BLOCKED.json").read_text())["reason"] == "DEVELOPMENT_GATE_TIMEOUT"


def test_gate_and_final_publish_distinct_timeout_terminals(tmp_path, monkeypatch):
    cfg = json.loads(json.dumps(CFG));cfg["runtime"]["output_root"]="out";cfg["runtime"]["provenance_root"]="prov";cfg["runtime"]["freeze"]="freeze.json"
    (tmp_path/"freeze.json").write_text("{}");(tmp_path/"prov").mkdir();assign=[{"endpoint":e,"model":m,"uuid":f"GPU-{e}-{m}"} for e in CFG["endpoints"] for m in ("gpt2","pythia160","gemma2")];(tmp_path/"prov/launch_manifest.json").write_text(json.dumps({"assignments":assign}))
    monkeypatch.setattr(v6,"ROOT",tmp_path);monkeypatch.setattr(v6,"loadj",lambda p:cfg if Path(p).name=="config.json" else json.loads(Path(p).read_text()));monkeypatch.setattr(v6,"verify_freeze",lambda *args:{});monkeypatch.setattr(v6,"wait_workers",lambda *args:(_ for _ in ()).throw(TimeoutError("forced")))
    with pytest.raises(TimeoutError):v6.development_gate(tmp_path/"config.json","retrieval")
    assert json.loads((tmp_path/"out/development_gate/retrieval/TIMEOUT.json").read_text())["status"]=="TIMEOUT"
    with pytest.raises(TimeoutError):v6.final_aggregate(tmp_path/"config.json")
    assert json.loads((tmp_path/"out/final/TIMEOUT.json").read_text())["status"]=="TIMEOUT"


def test_final_reports_upstream_gate_failure_without_missing_result_error(tmp_path, monkeypatch):
    cfg = json.loads(json.dumps(CFG));cfg["runtime"]["output_root"]="out";cfg["runtime"]["provenance_root"]="prov";cfg["runtime"]["freeze"]="freeze.json"
    (tmp_path/"freeze.json").write_text("{}");(tmp_path/"prov").mkdir();(tmp_path/"prov/launch_manifest.json").write_text('{"assignments":[]}')
    gate=tmp_path/"out/development_gate/retrieval";gate.mkdir(parents=True);(gate/"FAILED.json").write_text('{"status":"FAILED"}')
    monkeypatch.setattr(v6,"ROOT",tmp_path);monkeypatch.setattr(v6,"loadj",lambda p:cfg if Path(p).name=="config.json" else json.loads(Path(p).read_text()));monkeypatch.setattr(v6,"verify_freeze",lambda *args:{});monkeypatch.setattr(v6,"wait_workers",lambda *args:None)
    with pytest.raises(RuntimeError,match="development gate failed retrieval"):
        v6.final_aggregate(tmp_path/"config.json")
    term=json.loads((tmp_path/"out/final/FAILED.json").read_text())
    assert term["status"]=="FAILED"
    assert term["error"]=="development gate failed retrieval"
    assert "FileNotFoundError" not in term["traceback"]


def test_registered_hash_known_vectors_are_full_width_and_match_v5_casefolding():
    payload = "20260811|dataset|train|7|window"
    expected = int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "little")
    assert v6.stable(20260811, "dataset", "train", 7, "window") == expected
    assert expected > 2**32
    assert v6.th("Alpha  Beta") == hashlib.sha256(b"alpha beta").hexdigest()
    assert v6.th("Alpha") == v6.th("alpha")


def test_gpu_uuid_guard_and_cache_index_hashing(tmp_path, monkeypatch):
    class Props:
        uuid = "abc"
    monkeypatch.setattr(v6.torch.cuda, "device_count", lambda: 1)
    monkeypatch.setattr(v6.torch.cuda, "get_device_properties", lambda _: Props())
    monkeypatch.setenv("EXPECTED_GPU_UUID", "GPU-abc")
    assert v6.runtime_gpu() == "GPU-abc"
    monkeypatch.setenv("EXPECTED_GPU_UUID", "GPU-def")
    with pytest.raises(RuntimeError, match="mismatch"):
        v6.runtime_gpu()
    shard = tmp_path / "model-00001-of-00001.safetensors"
    shard.write_bytes(b"weights")
    index = tmp_path / "model.safetensors.index.json"
    index.write_text('{"weight_map":{"x":"model-00001-of-00001.safetensors"}}')
    (tmp_path / "config.json").write_text("{}")
    a = {r["name"]: r["sha256"] for r in v6.v5.cached_asset_records(tmp_path)}
    index.write_text('{"weight_map":{"y":"model-00001-of-00001.safetensors"}}')
    b = {r["name"]: r["sha256"] for r in v6.v5.cached_asset_records(tmp_path)}
    assert a["model.safetensors.index.json"] != b["model.safetensors.index.json"]


def test_no_training_or_representation_method_execution_path():
    text = (ROOT / "scripts/behavioral_endpoint_v6_2.py").read_text().lower()
    for forbidden in ("optimizer", "backward(", "load_public_sae", "fit_basis(", "representation_method_worker"):
        assert forbidden not in text
    assert "automodelforcausallm" in text


def test_launcher_never_rewrites_manifest_and_publishes_create_once_handoff():
    text = (ROOT / "scripts/launch_behavioral_endpoint_v6_2_tmux.sh").read_text()
    assert "open(manifest,'w')" not in text
    assert '"$PROV/handoff_status.json"' in text
    assert "os.O_EXCL" in text
    assert "launch_manifest_sha256" in text
