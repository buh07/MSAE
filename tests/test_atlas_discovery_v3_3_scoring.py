from __future__ import annotations

import sys
import json
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
from extract_atlas_discovery_v3_3 import (
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
    import extract_atlas_discovery_v3_3 as extraction

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

from extract_atlas_discovery_v3_3 import _qa_panel_units,_qa_stat
from atlas_discovery_v3_3_analysis import CategoricalEncoder,basis_overlap,choose_alpha,delta_basis,fit_ridge,macro_f1,make_projector


def test_signed_qa_stat_reports_failure_magnitude() -> None:
    ref=np.asarray([[1.0,2.0],[3.0,4.0]],dtype=np.float32)
    good=_qa_stat(ref,ref+1e-7,atol=5e-7,rtol=5e-6)
    assert good['status']=='PASS' and good['failing_rows']==0
    bad=_qa_stat(ref,ref+1e-2,atol=5e-7,rtol=5e-6)
    assert bad['status']=='FAIL' and bad['failing_rows']==2 and bad['max_bound_ratio']>1


def test_closed_form_ridge_is_deterministic_and_separates_signal() -> None:
    rng=np.random.default_rng(7);x=rng.normal(size=(100,5));y=np.where(x[:,0]>0,'a','b');folds=np.arange(100)%5
    a,grid=choose_alpha(x,y,folds,('a','b'),(.1,1.,10.,100.))
    one=fit_ridge(x,y,('a','b'),a);two=fit_ridge(x,y,('a','b'),a)
    np.testing.assert_array_equal(one.coef,two.coef)
    assert macro_f1(y,one.predict(x),('a','b'))>.9


def test_categorical_unknown_is_explicit_and_basis_overlap_behaves() -> None:
    enc=CategoricalEncoder.fit([{'x':'b'},{'x':'a'}],('x',))
    transformed=enc.transform([{'x':'never_seen'}])
    assert transformed.shape[0]==1 and transformed.sum()==1
    eye=np.eye(4)
    assert basis_overlap(eye[:,:2],eye[:,:2])==pytest.approx(1.0)
    assert basis_overlap(eye[:,:2],eye[:,2:])==pytest.approx(0.0)


def test_compact_qa_parent_has_exact_file_allowlist() -> None:
    root=Path(__file__).resolve().parents[1]/'data/atlas_discovery_v3_3_attempt7_qa_compact_v3/prepared'
    for source in ('EWT','GUM'):
        assert {p.name for p in (root/source).iterdir() if p.is_file()}=={'activation_rows.jsonl','inference_units.jsonl','intervention_pairs.jsonl'}


def test_compact_qa_lineage_and_ledger_are_technical_only() -> None:
    root=Path(__file__).resolve().parents[1]
    prepared=root/'data/atlas_discovery_v3_3_attempt7_qa_compact_v3/prepared'
    ledger=json.loads((prepared.parent/'opened_input_ledger.json').read_text())
    assert ledger['scope']=='external_devtest_technical_numerical_qa_only_no_scientific_population_construction'
    assert ledger['constructed_families']==['context_factorial','relative_gap']
    assert ledger['science_population_constructors_invoked'] is False
    assert set(ledger)=={
        'schema_version','scope','config','protocol','sources','model','constructed_families',
        'science_population_constructors_invoked','persisted_conditions','scientific_or_activation_outcomes_opened',
        'forbidden_or_blind_inputs_opened',
    }
    for source in ('EWT','GUM'):
        units=[json.loads(line) for line in (prepared/source/'inference_units.jsonl').read_text().splitlines() if line]
        rows=[json.loads(line) for line in (prepared/source/'activation_rows.jsonl').read_text().splitlines() if line]
        pairs=[json.loads(line) for line in (prepared/source/'intervention_pairs.jsonl').read_text().splitlines() if line]
        flattened=[row_id for unit in units for row_id in unit['row_ids']]
        ordered=[row['row_id'] for row in rows]
        assert flattened==ordered and len(ordered)==len(set(ordered))
        known=set(ordered);referenced=set()
        def collect(value):
            if isinstance(value,str):referenced.add(value)
            elif isinstance(value,dict):
                for child in value.values():collect(child)
        for pair in pairs:collect(pair['rows'])
        assert referenced==known
        assert {pair['construct'] for pair in pairs}=={'context_factorial','relative_gap'}
        for pair in pairs:
            expected={'relative_gap':{'bare','uniform_shift'},'context_factorial':{'bare','prefix_position_only'}}[pair['construct']]
            assert set(pair['rows'])==expected


def test_exact_legacy_and_external_fresh_panels_resolve_without_overlap() -> None:
    root=Path(__file__).resolve().parents[1];split=json.loads((root/'configs/atlas_discovery_v3_3/population_split_v3.json').read_text())
    parents={
        'legacy':(json.loads((root/'configs/atlas_discovery_v3/run.json').read_text()),json.loads((root/'data/atlas_discovery_v3_1_attempt5/prepared/manifest.json').read_text())),
        'fresh':(json.loads((root/'configs/atlas_discovery_v3_3/qa_compact_v3.json').read_text()),json.loads((root/'data/atlas_discovery_v3_3_attempt7_qa_compact_v3/prepared/manifest.json').read_text())),
    }
    for source in ('EWT','GUM'):
        docs={}
        for panel,(config,manifest) in parents.items():
            bundle=_load_source_bundle(config,manifest,source);refs,candidates,rows,segments=_qa_panel_units(bundle,split['sources'][source][f'{panel}_pair_ids'],json.loads((root/'configs/atlas_discovery_v3_3/run_final_v3.json').read_text()),panel=panel)
            assert len(rows)==(32 if panel=='legacy' else 16)
            assert {(s['family'],s['stop']-s['start']) for s in segments}==({('uniform_shift',32),('prefix_position_only',16)} if panel=='legacy' else {('uniform_shift',16),('prefix_position_only',8)})
            docs[panel]=set(split['sources'][source][f'{panel}_documents'])
        assert docs['legacy'].isdisjoint(docs['fresh'])


def test_attempt5_terminal_rejects_scoring_lineage_substitution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import prepare_atlas_discovery_v3_3_split as split_builder
    real=json.loads(split_builder.TERMINAL.read_text())
    real['payload']['scoring_config']['sha256']='0'*64
    substitute=tmp_path/'TERMINAL.json';substitute.write_text(json.dumps(real))
    monkeypatch.setattr(split_builder,'TERMINAL',substitute)
    with pytest.raises(RuntimeError,match='does not bind'):
        split_builder.verify_attempt5_terminal()


def test_attempt5_terminal_rejects_signer_substitution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import base64,hashlib
    import prepare_atlas_discovery_v3_3_split as split_builder
    config=json.loads(split_builder.ATTEMPT5_SCORING_CONFIG.read_text())
    attacker=Ed25519PrivateKey.generate().public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    config['qa_signer']['public_key_base64']=base64.b64encode(attacker).decode()
    config['qa_signer']['public_key_fingerprint_sha256']=hashlib.sha256(attacker).hexdigest()
    substitute=tmp_path/'scoring.json';substitute.write_text(json.dumps(config,sort_keys=True))
    monkeypatch.setattr(split_builder,'ATTEMPT5_SCORING_CONFIG',substitute)
    monkeypatch.setattr(split_builder,'EXPECTED_ATTEMPT5_SCORING_SHA256',hashlib.sha256(substitute.read_bytes()).hexdigest())
    with pytest.raises(RuntimeError,match='signer fingerprint drift'):
        split_builder.verify_attempt5_terminal()


def test_nuisance_only_fixture_has_no_representation_rescue() -> None:
    rows=[{'n':str(i%2)} for i in range(100)];y=np.asarray(['a' if i%2 else 'b' for i in range(100)]);folds=np.arange(100)%5
    enc=CategoricalEncoder.fit(rows,('n',));n=enc.transform(rows);representation=np.zeros((100,3));combined=np.concatenate([representation,n],axis=1)
    alpha_n,_=choose_alpha(n,y,folds,('a','b'),(.1,1.,10.,100.));alpha_c,_=choose_alpha(combined,y,folds,('a','b'),(.1,1.,10.,100.))
    npred=fit_ridge(n,y,('a','b'),alpha_n).predict(n);cpred=fit_ridge(combined,y,('a','b'),alpha_c).predict(combined)
    np.testing.assert_array_equal(npred,cpred)


def test_missing_training_class_and_zero_delta_fail_closed() -> None:
    x=np.arange(30,dtype=float).reshape(10,3);y=np.asarray(['a']*5+['b']*5);folds=np.asarray([0]*5+[1,2,3,4,4])
    with pytest.raises(ValueError,match='missing class'):
        choose_alpha(x,y,folds,('a','b'),(.1,))
    with pytest.raises(ValueError,match='zero delta'):
        delta_basis(np.zeros((4,3)),2,1e-8)


def test_projection_and_delta_basis_recover_planted_orthogonal_factors() -> None:
    rng=np.random.default_rng(4);a=np.c_[rng.normal(size=(40,2)),np.zeros((40,2))];b=np.c_[np.zeros((40,2)),rng.normal(size=(40,2))]
    ba,_=delta_basis(a,2,1e-8);bb,_=delta_basis(b,2,1e-8)
    assert basis_overlap(ba,bb)<1e-12
    p,diag=make_projector([ba],2,1e-8)
    assert diag['rank']==2
    assert np.mean(np.sum((a@p)**2,axis=1)/np.sum(a*a,axis=1))>0.999
    assert np.mean(np.sum((b@p)**2,axis=1)/np.sum(b*b,axis=1))<1e-12
