import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import recover_joint_controllability_v3_analysis as recovery


def test_native_converts_numpy_scalars_recursively():
    got = recovery.native({"flag": np.bool_(True), "count": np.int64(3), "value": [np.float64(1.5)]})
    assert got == {"flag": True, "count": 3, "value": [1.5]}
    assert json.loads(json.dumps(got)) == got


def test_exclusive_json_refuses_overwrite(tmp_path: Path):
    path = tmp_path / "result.json"
    recovery.exclusive_json(path, {"ok": np.bool_(True)})
    with pytest.raises(FileExistsError):
        recovery.exclusive_json(path, {"ok": False})


def test_recovery_has_no_model_or_training_imports():
    text = Path(recovery.__file__).read_text().lower()
    assert "transformers" not in text
    assert "torch" not in text
    assert "from_pretrained" not in text
    assert "optimizer" not in text


def test_recovery_import_does_not_load_torch_or_transformers():
    command = "import sys; import recover_joint_controllability_v3_analysis; assert 'torch' not in sys.modules; assert 'transformers' not in sys.modules"
    subprocess.run([sys.executable, "-c", command], check=True, env={**__import__('os').environ, "PYTHONPATH": str(Path(recovery.__file__).parent)})


def test_recovery_rejects_output_inside_preserved_source(tmp_path: Path):
    bad = recovery.DEFAULT_SOURCE / "forbidden_recovery"
    with pytest.raises(RuntimeError, match="output namespace is fixed"):
        recovery.recover(recovery.DEFAULT_SOURCE, bad)


def test_block_interval_golden_fixture():
    got = recovery.block_interval([1.0, 3.0, 2.0, 8.0], ["a", "a", "b", "c"], 50, 123)
    assert got == pytest.approx([2.0, 4.0, 6.0])


def test_exact_tree_rejects_extra_missing_and_changed_records():
    expected = [{"path": "source/a", "bytes": 1, "sha256": "a"}]
    recovery.require_exact_tree(expected, expected)
    for actual in ([], expected + [{"path": "source/b", "bytes": 0, "sha256": "b"}], [{**expected[0], "sha256": "changed"}]):
        with pytest.raises(RuntimeError, match="source-tree"):
            recovery.require_exact_tree(actual, expected)
