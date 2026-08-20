from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key as generate_rsa_private_key

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT / "scripts"))

import atlas_relation_context_v9 as common
import run_atlas_relation_context_v9 as runner
from analyze_atlas_relation_context_v9 import _evaluate_direction, _post_norm_support
from build_atlas_relation_context_v9 import _match_relations


def test_normalized_delta_is_scale_normalized_float64() -> None:
    left = np.asarray([[3, 4], [0, 0]], dtype=np.float32)
    right = np.asarray([[0, 0], [0, 0]], dtype=np.float32)
    value = common.normalized_delta(left, right)
    assert value.dtype == np.float64
    assert value.tolist() == [1.0, 0.0]


def test_relation_norm_inclusive_boundary_and_union_cap() -> None:
    variants = {
        "true": np.asarray([1e-4, 1.0, 1.0]),
        "sham": np.asarray([1.0, 1e-4, 1.0]),
        "sequential_offset": np.asarray([1.0, 1.0, 1e-4]),
    }
    audit = common.relation_norm_audit(variants, threshold=1e-4, maximum_rate=1 / 3)
    assert audit["denominator"] == 3
    assert audit["variant_noninformative_counts"] == {"true": 1, "sham": 1, "sequential_offset": 1}
    assert audit["union_noninformative_count"] == 3
    assert audit["cap_pass"] is False  # union, not just each variant, is capped
    assert not audit["informative_mask"].any()


def test_component_bootstrap_is_shared_and_deterministic() -> None:
    components = [f"component:{index}" for index in range(10)]
    left = common.component_multiplicities(components, direction="A_to_B", endpoint="relation:x", draw=17, seed=9)
    right = common.component_multiplicities(components, direction="A_to_B", endpoint="relation:x", draw=17, seed=9)
    assert left == right
    assert sum(left.values()) == 10


def test_global_study_key_excludes_authorization_identity() -> None:
    config = common.read_json(common.CONFIG)
    first = common.study_key(config)
    changed = json.loads(json.dumps(config)); changed["authorization_nonce"] = "successor"
    assert common.study_key(changed) == first


def test_same_study_key_does_not_make_altered_config_executable(tmp_path: Path) -> None:
    config = common.read_json(common.CONFIG)
    altered = json.loads(json.dumps(config))
    altered["model"]["hidden_state_index"] += 1
    altered["model"]["batch_size"] += 1
    altered["runtime"]["physical_gpu_index"] += 1
    altered["analysis"]["ridge_alpha_selection"] = "outcome_conditioned"
    assert common.study_key(altered) == common.study_key(config)
    path = tmp_path / "same-key-altered-config.json"
    path.write_text(json.dumps(altered))
    missing_key = tmp_path / "must-not-be-read.pem"
    with pytest.raises(RuntimeError, match="canonical frozen config"):
        runner.authorize(path, missing_key)
    with pytest.raises(RuntimeError, match="canonical frozen config"):
        runner.execute(path, missing_key)


def test_global_study_key_cannot_be_consumed_twice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(common, "GLOBAL_OPENING_ROOT", tmp_path)
    config = common.read_json(common.CONFIG)
    common.consume_study_key(config, {"status": "first"})
    with pytest.raises(FileExistsError):
        common.consume_study_key(config, {"status": "successor authorization"})


def _write_private_key(path: Path, private: object) -> None:
    path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def test_lifecycle_signer_rejects_wrong_ed25519_and_wrong_key_type(tmp_path: Path) -> None:
    signer = common.read_json(common.CONFIG)["signer"]
    wrong_ed25519 = tmp_path / "wrong-ed25519.pem"
    _write_private_key(wrong_ed25519, Ed25519PrivateKey.generate())
    with pytest.raises(RuntimeError, match="does not match"):
        common.load_signing_key(wrong_ed25519, signer)

    wrong_rsa = tmp_path / "wrong-rsa.pem"
    _write_private_key(wrong_rsa, generate_rsa_private_key(public_exponent=65537, key_size=2048))
    with pytest.raises(RuntimeError, match="not Ed25519"):
        common.load_signing_key(wrong_rsa, signer)


def test_wrong_signer_fails_before_namespace_or_study_consumption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = {"signer": common.read_json(common.CONFIG)["signer"]}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    wrong = tmp_path / "wrong.pem"
    _write_private_key(wrong, Ed25519PrivateKey.generate())
    run_root, result_root, opening_root = tmp_path / "run", tmp_path / "result", tmp_path / "openings"
    monkeypatch.setattr(runner, "RUN_ROOT", run_root)
    monkeypatch.setattr(runner, "RESULT_ROOT", result_root)
    monkeypatch.setattr(runner, "CONFIG", config_path)
    monkeypatch.setattr(runner, "_verify_config", lambda _: None)
    monkeypatch.setattr(common, "GLOBAL_OPENING_ROOT", opening_root)
    with pytest.raises(RuntimeError, match="does not match"):
        runner.execute(config_path, wrong)
    assert not run_root.exists()
    assert not result_root.exists()
    assert not opening_root.exists()


def test_block_review_cannot_be_promoted_by_declared_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = tmp_path / "freeze.json"
    payload.write_text("frozen\n")
    monkeypatch.setattr(common, "FINAL_FREEZE_PAYLOAD", payload)
    inventory = "a" * 64
    freeze = {"candidate_inventory_sha256": inventory}
    review = tmp_path / "review.md"
    review.write_text(
        "VERDICT: BLOCK\n"
        f"FINAL_FREEZE_PAYLOAD_SHA256: {common.sha256_file(payload)}\n"
        f"CANDIDATE_INVENTORY_SHA256: {inventory}\n"
        "VERDICT: SHIP\n"
    )
    with pytest.raises(RuntimeError, match="VERDICT: SHIP"):
        common.verify_candidate_review(review, freeze)


def test_detached_freezes_verify_under_frozen_signer() -> None:
    config = common.read_json(common.CONFIG)
    fingerprint = config["signer"]["public_key_fingerprint_sha256"]
    common.verify_detached(common.HISTORICAL_PAYLOAD, common.HISTORICAL_ENVELOPE, expected_public_fingerprint=fingerprint)
    common.verify_detached(common.FINAL_FREEZE_PAYLOAD, common.FINAL_FREEZE_ENVELOPE, expected_public_fingerprint=fingerprint)


def test_reconciliation_rejects_unclassified_late_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("historical.json", "historical.env", "freeze.json", "freeze.env", "review.md"):
        (tmp_path / name).write_text(name)
    historical = {
        "entries": [
            {"path": "baseline.txt", "bytes": 4, "sha256": __import__("hashlib").sha256(b"base").hexdigest()}
        ]
    }
    (tmp_path / "baseline.txt").write_text("base")
    (tmp_path / "historical.json").write_text(json.dumps(historical))
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(common, "HISTORICAL_PAYLOAD", tmp_path / "historical.json")
    monkeypatch.setattr(common, "HISTORICAL_ENVELOPE", tmp_path / "historical.env")
    monkeypatch.setattr(common, "FINAL_FREEZE_PAYLOAD", tmp_path / "freeze.json")
    monkeypatch.setattr(common, "FINAL_FREEZE_ENVELOPE", tmp_path / "freeze.env")
    monkeypatch.setattr(common, "CANDIDATE_REVIEW", tmp_path / "review.md")
    monkeypatch.setattr(common, "AUTHORIZATION", tmp_path / "authorization.json")
    monkeypatch.setattr(common, "RUN_ROOT", tmp_path / "run")
    monkeypatch.setattr(common, "RESULT_ROOT", tmp_path / "result")
    freeze = {"candidate_entries": []}
    # Manifest/envelope/review are exact late artifacts; an extra file is not.
    (tmp_path / "unexpected.txt").write_text("late")
    with pytest.raises(RuntimeError, match="unclassified late"):
        common.reconcile_frozen_tree(freeze, stage="preauthorization")


def test_reconciliation_rejects_unclassified_directory_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "baseline.txt").write_text("base")
    historical = {
        "entries": [
            {"path": "baseline.txt", "bytes": 4, "sha256": common.sha256_file(tmp_path / "baseline.txt")}
        ]
    }
    (tmp_path / "historical.json").write_text(json.dumps(historical))
    (tmp_path / "historical.env").write_text("historical-envelope")
    for name in ("freeze.json", "freeze.env", "review.md"):
        (tmp_path / name).write_text(name)
    (tmp_path / "real-directory").mkdir()
    (tmp_path / "late-directory-link").symlink_to(tmp_path / "real-directory", target_is_directory=True)
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(common, "HISTORICAL_PAYLOAD", tmp_path / "historical.json")
    monkeypatch.setattr(common, "HISTORICAL_ENVELOPE", tmp_path / "historical.env")
    monkeypatch.setattr(common, "FINAL_FREEZE_PAYLOAD", tmp_path / "freeze.json")
    monkeypatch.setattr(common, "FINAL_FREEZE_ENVELOPE", tmp_path / "freeze.env")
    monkeypatch.setattr(common, "CANDIDATE_REVIEW", tmp_path / "review.md")
    monkeypatch.setattr(common, "AUTHORIZATION", tmp_path / "authorization.json")
    monkeypatch.setattr(common, "RUN_ROOT", tmp_path / "run")
    monkeypatch.setattr(common, "RESULT_ROOT", tmp_path / "result")
    entries = []
    for name in ("historical.json", "historical.env"):
        path = tmp_path / name
        entries.append({"path": name, "bytes": path.stat().st_size, "sha256": common.sha256_file(path)})
    freeze = {"candidate_entries": entries}
    with pytest.raises(RuntimeError, match="late-directory-link/"):
        common.reconcile_frozen_tree(freeze, stage="preauthorization")


def _synthetic_relation_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(20):
        rows.append(
            {
                "document_group": f"S:t{index}",
                "donor_document_group": f"S:d{index}",
                "component_id": f"c{index // 2}",
                "fold": (index // 2) % 5,
                "labels": {"dependency_depth": "A" if index < 10 else "B"},
            }
        )
    return rows


def test_post_norm_support_loss_fails_closed_without_backfill() -> None:
    rows = _synthetic_relation_rows()
    assert _post_norm_support(rows, "dependency_depth", ("A", "B"), 1)["eligible"] is True
    after_union_exclusion = rows[1:]
    result = _post_norm_support(after_union_exclusion, "dependency_depth", ("A", "B"), 1)
    assert result["target_documents"] == 19
    assert result["class_documents"]["A"] == 9
    assert result["eligible"] is False


def test_ephemeral_ridge_direction_smoke_does_not_persist_weights() -> None:
    rows = []
    variants: dict[str, list[list[float]]] = {name: [] for name in ("child", "true", "sham", "sequential_offset")}
    for index in range(20):
        label = "A" if index % 2 == 0 else "B"
        rows.append({"row_id": str(index), "labels": {"dependency_depth": label}, "fold": (index // 2) % 5, "component_id": f"c{index // 2}"})
        variants["child"].append([0.0, 0.0])
        variants["sham"].append([0.0, 0.0])
        variants["sequential_offset"].append([0.0, 0.0])
        variants["true"].append([1.0, 0.0] if label == "A" else [0.0, 1.0])

    class Fake:
        source = "S"

        def matrix(self, selected, variant):  # noqa: ANN001
            return np.asarray([variants[variant][int(row["row_id"])] for row in selected], dtype=np.float64)

    config = common.read_json(common.CONFIG)
    config = json.loads(json.dumps(config)); config["analysis"]["ridge_device"] = "cpu"; config["analysis"]["alphas"] = [1.0]
    output = _evaluate_direction(Fake(), Fake(), rows, rows, "dependency_depth", ("A", "B"), config)
    assert output["raw_decodability_pass"] is True
    assert output["macro_f1"]["true"] == 1.0
    assert not list(ROOT.glob("**/*coef*attempt13*"))


def test_exact_relation_control_is_source_local_componentized_and_reuse_capped() -> None:
    stratum = (0, 2, 3, "NOMINAL", "VERBAL", "8-15")
    targets = []
    donors: dict[str, list[dict[str, object]]] = {}
    for doc in ("a", "b"):
        targets.append(
            {
                "target_id": f"S:{doc}:t",
                "source": "S",
                "document": doc,
                "fold": 0,
                "stratum": stratum,
                "child_row_id": f"{doc}:child",
                "head_row_id": f"{doc}:head",
                "sham_row_id": f"{doc}:sham",
                "labels": {"dependency_depth": "1", "deprel_coarse": "CORE", "head_signed_distance": "R2"},
            }
        )
        donors[doc] = [
            {
                "donor_id": f"S:{doc}:d",
                "source": "S",
                "document": doc,
                "fold": 0,
                "stratum": stratum,
                "child_row_id": f"{doc}:donor-child",
                "candidate_row_id": f"{doc}:donor-candidate",
            }
        ]
    rows, report = _match_relations("S", targets, donors)
    assert report["document_pair_components"] == 1
    assert len(rows) == 2
    assert len({row["donor_candidate_row_id"] for row in rows}) == 2
    for row in rows:
        assert row["source"] == "S"
        assert row["document_group"] != row["donor_document_group"]
        assert row["exact_signed_ud_distance"] == 2
        assert row["exact_signed_subtoken_offset"] == 3
        assert len(row["component_documents"]) == 2


def test_frozen_collision_census_and_prepared_backstop() -> None:
    census = common.read_json(ROOT / "reports/provenance/atlas_v3_9_attempt13_collision_census.json")
    assert census["activation_or_endpoint_result_used"] is False
    assert census["sources"]["GENTLE"] == {
        "affected_documents": 7,
        "amended_removed_documents": 2,
        "amended_removed_sentences_only": 5,
        "collided_sentences": 12,
        "maximum_isolated_short_ud_word_count": 5,
        "remaining_documents": 24,
    }
    excluded = {
        source: [row["signature"]["selected_subtoken_ids"] for row in census["collisions"] if row["source"] == source]
        for source in ("GENTLE", "CTETEX")
    }
    firewall = common.read_json(common.DATA_ROOT / "exposure_firewall.json")
    for source in ("GENTLE", "CTETEX"):
        gap_docs = set(firewall["removed_documents"][source]["context_gap_documents"])
        pairs = common.read_jsonl(common.PREPARED_ROOT / source / "intervention_pairs.jsonl")
        assert not any(row["construct"] == "context_factorial" and row["document_group"].split(":", 1)[1] in gap_docs for row in pairs)
        for unit in common.read_jsonl(common.PREPARED_ROOT / source / "inference_units.jsonl"):
            ids = unit["input_ids"]
            assert not any(
                sequence
                and any(ids[index : index + len(sequence)] == sequence for index in range(len(ids) - len(sequence) + 1))
                for sequence in excluded[source]
            )


def test_prescore_support_is_endpoint_specific() -> None:
    manifest = common.read_json(common.PREPARED_ROOT / "manifest.json")
    assert manifest["authorization_eligible"] is True
    assert manifest["module_prescore"] == {
        "GENTLE": {"relation": True, "secondary": False},
        "CTETEX": {"relation": True, "secondary": False},
    }
    assert manifest["sources"]["GENTLE"]["relation_support"]["components"] == 10
    assert manifest["sources"]["GENTLE"]["intervention_support"]["context_factorial"]["eligible"] is False


def test_attempt12_is_byte_identical() -> None:
    expected = common.read_json(ROOT / common.read_json(common.CONFIG)["attempt12_inventory"]["path"])
    common.assert_attempt12_inventory(expected)


def test_new_python_has_no_neural_training_or_checkpoint_calls() -> None:
    names = (
        "atlas_relation_context_v9.py",
        "build_atlas_relation_context_v9.py",
        "analyze_atlas_relation_context_v9.py",
        "run_atlas_relation_context_v9.py",
    )
    forbidden = {"backward", "step", "train", "save_pretrained", "save_checkpoint"}
    observed: list[str] = []
    for name in names:
        tree = ast.parse((ROOT / "scripts" / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                target = node.func.attr if isinstance(node.func, ast.Attribute) else (node.func.id if isinstance(node.func, ast.Name) else "")
                if target in forbidden:
                    observed.append(f"{name}:{target}")
    assert observed == []
