from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from atlas_discovery_v3_scoring import (
    derive_numerical_tolerance,
    elementwise_null_pass,
    independent_prior_macro_f1,
    normalized_recovery,
    resolve_hidden_state_index,
)
from extract_atlas_discovery_v3 import (
    _assert_translation,
    _exclusive_lock,
    _forward_units,
    _load_source_bundle,
    _new_staging,
    _promote,
    _sign_payload,
    _verify_authorized_signer,
    _verify_envelope,
)


def test_hidden_state_layer_resolution_matches_block_output() -> None:
    assert resolve_hidden_state_index(3, 13) == 4
    with pytest.raises(ValueError, match="exceeds"):
        resolve_hidden_state_index(99, 13)


def test_derived_tolerance_is_frozen_and_fail_closed() -> None:
    good = derive_numerical_tolerance(
        2e-7, atol_floor=5e-7, atol_hard_ceiling=2e-5, multiplier=2.0, rtol=5e-6
    )
    assert good == {"status": "valid", "max_abs_repeat_error": 2e-7, "atol": 5e-7, "rtol": 5e-6}
    bad = derive_numerical_tolerance(
        1e-5, atol_floor=5e-7, atol_hard_ceiling=2e-5, multiplier=2.0, rtol=5e-6
    )
    assert bad["status"] == "invalid"
    assert bad["atol"] is None
    with pytest.raises(ValueError):
        derive_numerical_tolerance(
            0.0, atol_floor=2e-5, atol_hard_ceiling=2e-5, multiplier=2.0, rtol=5e-6
        )


def test_elementwise_null_uses_atol_plus_rtol_reference() -> None:
    reference = np.asarray([[1.0, 2.0]])
    assert elementwise_null_pass(reference, reference + 5e-6, atol=1e-6, rtol=5e-6)
    assert not elementwise_null_pass(reference, reference + 2e-5, atol=1e-6, rtol=5e-6)


def test_independent_prior_chance_and_recovery() -> None:
    chance = independent_prior_macro_f1(
        np.asarray([0.75, 0.25]), np.asarray([0.5, 0.5])
    )
    assert chance == pytest.approx(((2 * .75 * .5 / 1.25) + (2 * .25 * .5 / .75)) / 2)
    assert normalized_recovery(chance, chance) == pytest.approx(0.0)
    assert normalized_recovery(1.0, chance) == pytest.approx(1.0)


def test_null_translation_rejects_token_or_nonconstant_position_change() -> None:
    reference = {
        "input_ids": [1, 2],
        "attention_mask": [1, 1],
        "position_ids": [0, 1],
        "positions": [0, 1],
        "row_ids": ["a", "b"],
    }
    _assert_translation(reference, {**reference, "position_ids": [16, 17], "row_ids": ["c", "d"]}, 16)
    with pytest.raises(RuntimeError, match="input_ids"):
        _assert_translation(reference, {**reference, "input_ids": [1, 3], "position_ids": [16, 17]}, 16)
    with pytest.raises(RuntimeError, match="translation"):
        _assert_translation(reference, {**reference, "position_ids": [16, 18]}, 16)


class _FakeOutput:
    def __init__(self, hidden: torch.Tensor) -> None:
        self.hidden_states = (hidden, hidden)


class _FakeModel:
    def __call__(self, *, input_ids, attention_mask, position_ids, output_hidden_states, use_cache):
        assert output_hidden_states and not use_cache
        hidden = torch.stack((input_ids.float(), position_ids.float()), dim=-1)
        hidden = hidden * attention_mask.unsqueeze(-1)
        return _FakeOutput(hidden)


def test_forward_units_preserves_multilength_target_order() -> None:
    units = [
        {"input_ids": [4, 5], "attention_mask": [1, 1], "position_ids": [8, 9], "positions": [1]},
        {"input_ids": [6, 7, 8], "attention_mask": [1, 1, 1], "position_ids": [1, 2, 3], "positions": [2, 0]},
    ]
    block = _forward_units(_FakeModel(), units, device=torch.device("cpu"), hidden_index=1, batch_size=2)
    np.testing.assert_array_equal(block, [[5, 9], [8, 3], [6, 1]])


def test_pinned_signer_rejects_untrusted_key(tmp_path: Path) -> None:
    trusted = Ed25519PrivateKey.generate()
    untrusted = Ed25519PrivateKey.generate()
    public = trusted.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    import base64, hashlib

    config = {
        "qa_signer": {
            "public_key_base64": base64.b64encode(public).decode(),
            "public_key_fingerprint_sha256": hashlib.sha256(public).hexdigest(),
        }
    }
    trusted_path = tmp_path / "trusted.pem"
    trusted_path.write_bytes(
        trusted.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    untrusted_path = tmp_path / "untrusted.pem"
    untrusted_path.write_bytes(
        untrusted.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    loaded = _verify_authorized_signer(config, trusted_path)
    envelope = _sign_payload({"status": "PASS"}, loaded)
    assert _verify_envelope(envelope, config)["status"] == "PASS"
    with pytest.raises(RuntimeError, match="does not match"):
        _verify_authorized_signer(config, untrusted_path)


def test_stage_lock_rejects_concurrent_holder(tmp_path: Path) -> None:
    with _exclusive_lock(tmp_path, "stage"):
        with pytest.raises(RuntimeError, match="concurrent"):
            with _exclusive_lock(tmp_path, "stage"):
                pass


def test_staging_rejects_stale_and_promotes_atomically(tmp_path: Path) -> None:
    stage = _new_staging(tmp_path, "qa-EWT", "a" * 64)
    (stage / "artifact").write_text("ok")
    final = tmp_path / "final"
    _promote(stage, final)
    assert (final / "artifact").read_text() == "ok"
    stale = tmp_path / "staging" / f"qa-GUM-{'b' * 12}-old"
    stale.mkdir()
    with pytest.raises(RuntimeError, match="stale staging"):
        _new_staging(tmp_path, "qa-GUM", "b" * 64)


def test_source_bundle_rejects_child_tampering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib, json
    import extract_atlas_discovery_v3 as extraction

    root = tmp_path / "data" / "prepared" / "EWT"
    root.mkdir(parents=True)
    unit = {
        "unit_id": "u",
        "input_ids": [1],
        "attention_mask": [1],
        "position_ids": [0],
        "positions": [0],
        "row_ids": ["r"],
    }
    paths = {
        "units": root / "inference_units.jsonl",
        "rows": root / "activation_rows.jsonl",
        "pairs": root / "intervention_pairs.jsonl",
    }
    paths["units"].write_text(json.dumps(unit) + "\n")
    paths["rows"].write_text(json.dumps({"row_id": "r"}) + "\n")
    paths["pairs"].write_text(json.dumps({"pair_id": "p", "rows": {"bare": "r"}}) + "\n")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "sources": {
            "EWT": {
                "units_sha256": digest(paths["units"]),
                "activation_rows_sha256": digest(paths["rows"]),
                "intervention_pairs_sha256": digest(paths["pairs"]),
            }
        }
    }
    monkeypatch.setattr(extraction, "ROOT", tmp_path)
    bundle = _load_source_bundle({"data_root": "data"}, manifest, "EWT")
    assert bundle["rows"][0]["row_id"] == "r"
    paths["units"].write_text(paths["units"].read_text() + "\n")
    with pytest.raises(RuntimeError, match="digest drift"):
        _load_source_bundle({"data_root": "data"}, manifest, "EWT")
