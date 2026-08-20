from __future__ import annotations
import inspect, json, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import run_atlas_rope_v6 as runner
import run_atlas_rope_v6_science as science

def test_frozen_science_contract_verifies():
    cfg=science.verify_frozen_contract()
    assert cfg['schema_version']=='atlas_rope_v6_attempt10_science_adapter_v1'
    assert cfg['claim_class']=='EXPLORATORY_GUM_TECHNICAL_CALIBRATION_DUAL_ROLE'
    assert cfg['neural_training_authorized'] is False

def test_frozen_scientific_files_match_attempt9_config():
    old=json.loads((ROOT/'configs/atlas_rope_v5/science_adapter.json').read_text())
    new=json.loads(science.ADAPTER_CONFIG.read_text())
    for key in ('frozen_files','frozen_function_hashes','frozen_analysis_settings','frozen_analysis_settings_sha256','frozen_scoring_config','frozen_science_prescore','frozen_prepared_manifest','frozen_rebuild','extraction','model'):
        assert new[key]==old[key]

def test_gum_bridge_explicitly_does_not_require_gum_pass():
    cfg=science.verify_frozen_contract()['technical_qa_bridge']
    assert cfg['attempt9_gum_pass_required'] is False
    src=inspect.getsource(science._qa_bridge_payload)
    assert 'GUM_PASS' not in src
    assert '_verify_gum_history' in src and '_verify_gum_sentinel_history' in src

def test_science_is_gentle_authorization_gated():
    with pytest.raises((FileNotFoundError,RuntimeError)):
        science._verify_science_authorization()

def test_science_result_namespace_is_attempt10():
    assert science.RESULT_ROOT==ROOT/'results/atlas_rope_v6_attempt10_science'
    assert science.SCIENCE_ROOT==runner.RUN_ROOT/'science'
    cfg=science.verify_frozen_contract()
    assert cfg['analysis_output']==str(science.RESULT_ROOT.relative_to(ROOT))
    assert cfg['science_run_root']==str(science.SCIENCE_ROOT.relative_to(ROOT))
    assert cfg['technical_science_authorization']==str(runner.SCIENCE_AUTHORIZATION.relative_to(ROOT))

def test_science_source_has_no_optimizer_or_backward_call():
    src=Path(science.__file__).read_text()
    assert '.backward(' not in src and 'torch.optim' not in src
    assert 'optimizer_created": False' in src
