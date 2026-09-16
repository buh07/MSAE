from __future__ import annotations

import importlib.util
import importlib._bootstrap_external
import inspect
import json
import os
from pathlib import Path
import stat
import signal
import copy
import subprocess
import sys
import time
import types
import base64
import contextlib

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _local_module in (
    "msae_independent_measurement_v3", "msae_independent_measurement_v3_post_m1",
    "msae_independent_measurement_v3_post_m1_runtime",
    "msae_independent_measurement_v3_post_m2_gen4",
    "msae_independent_measurement_v3_post_m2_gen4_runtime",
    "msae_measurement_remediation_v1", "msae_measurement_v2",
    "run_msae_independent_calibration_v3", "run_msae_independent_calibration_v3_gen4",
):
    sys.modules.pop(_local_module, None)
_controller_path = ROOT / "scripts/msae_independent_measurement_v3_post_m2_gen4.py"
_controller = types.ModuleType("msae_independent_measurement_v3_post_m2_gen4")
_controller.__file__ = str(_controller_path)
_controller.__package__ = None
sys.modules[_controller.__name__] = _controller
exec(compile(_controller_path.read_bytes(), str(_controller_path), "exec"), _controller.__dict__)
SPEC = _controller.source_only_module_spec(
    "msae_v3_post_m2_runtime",
    ROOT / "scripts/msae_independent_measurement_v3_post_m2_gen4_runtime.py")
assert SPEC and SPEC.loader
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


def _write_timestamp_valid_malicious_pyc(source: Path, marker: Path) -> Path:
    """Plant bytecode that is valid for the untouched source's mtime/size."""
    source_stat = source.stat()
    payload = (
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('malicious-pyc-executed')\n"
    )
    code = compile(payload, str(source), "exec")
    raw = importlib._bootstrap_external._code_to_timestamp_pyc(  # type: ignore[attr-defined]
        code, int(source_stat.st_mtime), source_stat.st_size)
    cached = Path(importlib.util.cache_from_source(str(source)))
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(raw)
    return cached


def _write_sourceless_malicious_pyc(path: Path, marker: Path) -> None:
    payload = (
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('sourceless-pyc-executed')\n"
    )
    code = compile(payload, str(path.with_suffix(".py")), "exec")
    raw = importlib._bootstrap_external._code_to_timestamp_pyc(  # type: ignore[attr-defined]
        code, 0, 0)
    path.write_bytes(raw)


def _copy_source_only_cli_fixture(root: Path) -> None:
    import shutil
    for name in (
        "msae_independent_measurement_v3.py",
        "msae_independent_measurement_v3_post_m1.py",
        "msae_independent_measurement_v3_post_m1_runtime.py",
        "msae_independent_measurement_v3_post_m2_gen4.py",
        "msae_independent_measurement_v3_post_m2_gen4_runtime.py",
        "msae_measurement_remediation_v1.py",
        "msae_measurement_v2.py",
        "run_msae_independent_calibration_v3.py",
        "run_msae_independent_calibration_v3_gen4.py",
    ):
        target = root / "scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "scripts" / name, target)


def test_controller_ignores_valid_timestamp_local_pyc_before_all_gates(tmp_path):
    candidate = tmp_path / "candidate"
    _copy_source_only_cli_fixture(candidate)
    source = candidate / "scripts/msae_independent_measurement_v3.py"
    marker = tmp_path / "controller-pyc-marker"
    _write_timestamp_valid_malicious_pyc(source, marker)
    python = str(ROOT / ".venv-atlas/bin/python")

    # Prove the planted cache is accepted by Python's default finder.
    control = subprocess.run([
        python, "-S", "-B", "-I", "-c",
        f"import sys;sys.path.insert(0,{str(source.parent)!r});"
        "import msae_independent_measurement_v3",
    ], text=True, capture_output=True)
    assert control.returncode == 0 and marker.read_text() == "malicious-pyc-executed"
    marker.unlink()

    # The reviewed controller runs as source and installs its exact finder
    # before the first local import.  It may fail later because the temp tree is
    # intentionally incomplete, but the valid malicious cache cannot execute.
    result = subprocess.run([
        python, "-S", "-B", "-I",
        str(candidate / "scripts/msae_independent_measurement_v3_post_m2_gen4.py"),
        "not-a-command",
    ], text=True, capture_output=True)
    assert result.returncode != 0
    assert not marker.exists()


def test_runner_ignores_valid_timestamp_controller_pyc_before_auth_gate(tmp_path):
    candidate = tmp_path / "candidate"
    _copy_source_only_cli_fixture(candidate)
    controller = candidate / "scripts/msae_independent_measurement_v3_post_m2_gen4.py"
    marker = tmp_path / "runner-pyc-marker"
    _write_timestamp_valid_malicious_pyc(controller, marker)
    result = subprocess.run([
        str(ROOT / ".venv-atlas/bin/python"), "-S", "-B", "-I",
        str(candidate / "scripts/run_msae_independent_calibration_v3_gen4.py"),
        "--run-root", "not-the-signed-root", "--gpu-uuid", "GPU-fake",
        "--broker-pid", "1", "--readiness-fd", "0", "--final-ack-fd", "0",
        "--confirmed-fd", "0",
    ], text=True, capture_output=True)
    assert result.returncode != 0
    assert not marker.exists()


def test_runner_removes_scripts_path_before_deferred_third_party_import(tmp_path):
    import shutil
    candidate = tmp_path / "candidate"
    _copy_source_only_cli_fixture(candidate)
    (candidate / ".venv-atlas").symlink_to(ROOT / ".venv-atlas", target_is_directory=True)
    m0 = candidate / "data/msae_independent_measurement_v3/m0_completion_manifest.json"
    m0.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "data/msae_independent_measurement_v3/m0_completion_manifest.json", m0)
    shadow = candidate / "scripts/numpy.pyc"
    marker = tmp_path / "sourceless-shadow-marker"
    _write_sourceless_malicious_pyc(shadow, marker)
    python = str(ROOT / ".venv-atlas/bin/python")

    # Prove a default PathFinder search of scripts executes the planted,
    # Git-ignored sourceless cache.
    control = subprocess.run([
        python, "-S", "-B", "-I", "-c",
        f"import sys;sys.path.insert(0,{str(shadow.parent)!r});import numpy",
    ], text=True, capture_output=True)
    assert control.returncode == 0 and marker.read_text() == "sourceless-pyc-executed"
    marker.unlink()

    runner = candidate / "scripts/run_msae_independent_calibration_v3_gen4.py"
    result = subprocess.run([
        python, "-S", "-B", "-I", "-c",
        "import runpy,sys;"
        f"runpy.run_path({str(runner)!r},run_name='msae_runner_source_only_probe');"
        "assert all(not p.endswith('/scripts') for p in sys.path);"
        "import numpy;print(numpy.__file__)",
    ], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "site-packages/numpy/__init__.py" in result.stdout
    assert not marker.exists()


def terminal_files():
    return {"stage_b.json": b"{}\n", "status.json": b"{}\n",
            "runtime_native_pre_import.json": b"{}\n",
            "runtime_native_post_torch.json": b"{}\n",
            "runtime_native_post_model.json": b"{}\n",
            "runtime_native_final.json": b"{}\n"}


def test_operator_instruction_is_verbatim_and_not_a_paraphrase():
    assert runtime.OPERATOR_INSTRUCTION.startswith("Do these steps for me.")
    assert "THanks!\n\n### 1. Preserve this attempt as failed" in runtime.OPERATOR_INSTRUCTION
    assert runtime.OPERATOR_INSTRUCTION.endswith("- add behavioral failure-path tests.")
    assert runtime.base.sha_bytes(runtime.OPERATOR_INSTRUCTION.encode("utf-8")) == \
        "8acd2583df6224ff357766296c1f4461212de5383f533ee352d292f9cbdaca12"


def test_endpoint_registry_is_closed_and_has_no_learned_c1_branch_names():
    registry = runtime.endpoint_registry()
    ids = [row["endpoint_id"] for row in registry["entries"]]
    assert len(ids) == len(set(ids)) == registry["endpoint_count"]
    categories = {row["category"] for row in registry["entries"]}
    assert categories == {"localization", "functional_reproducibility", "collateral",
                          "counterfactual", "baseline"}
    c1 = [row for row in registry["entries"] if row.get("role") == "C1"]
    assert all(row.get("checkpoint") in {None, "raw"} for row in c1)
    assert all(row.get("component") not in {"assigned", "nonassigned", "joint"} for row in c1)
    repro = [row for row in registry["entries"] if row["category"] == "functional_reproducibility"]
    assert all(row["checkpoints"] == ["g4", "g5", "g6"] and row["control"] == "g7_descriptive_only"
               for row in repro)
    assert registry["endpoint_count"] == 1541
    assert registry["category_counts"] == {
        "localization": 576, "functional_reproducibility": 33, "collateral": 792,
        "counterfactual": 96, "baseline": 44}
    assert all(row.get("component") for row in registry["entries"]
               if row["category"] == "collateral")


def test_endpoint_registry_rejects_noncanonical_endpoint_id():
    value = copy.deepcopy(runtime.endpoint_registry())
    value["entries"][0]["endpoint_id"] = "arbitrary-but-unique"
    value["endpoint_id_set_sha256"] = runtime.base.sha_bytes(runtime.base.canonical_bytes(
        sorted(row["endpoint_id"] for row in value["entries"])))
    with pytest.raises(ValueError, match="canonical typed-key"):
        runtime.validate_endpoint_registry(value)


@pytest.mark.parametrize("field,replacement", [
    ("role", "C9"), ("checkpoint", "g9"), ("family", "missing_family"),
    ("task", "missing_task"), ("component", "missing_component"),
    ("metric", "missing_metric"), ("layer", 4),
])
def test_endpoint_registry_rejects_every_localization_axis_mutation(field, replacement):
    value = copy.deepcopy(runtime.endpoint_registry())
    row = next(item for item in value["entries"] if item["category"] == "localization")
    row[field] = replacement
    with pytest.raises(ValueError, match="endpoint product mismatch"):
        runtime.validate_endpoint_registry(value)


def test_endpoint_registry_rejects_missing_g7_c1_and_duplicate_cells():
    original = runtime.endpoint_registry()
    for predicate in (
        lambda row: row.get("checkpoint") == "g7",
        lambda row: row.get("role") == "C1",
    ):
        value = copy.deepcopy(original)
        index = next(i for i, row in enumerate(value["entries"]) if predicate(row))
        value["entries"].pop(index)
        with pytest.raises(ValueError, match="endpoint product mismatch"):
            runtime.validate_endpoint_registry(value)
    value = copy.deepcopy(original)
    value["entries"].append(copy.deepcopy(value["entries"][0]))
    with pytest.raises(ValueError, match="endpoint product mismatch"):
        runtime.validate_endpoint_registry(value)


def _minimal_config_candidate_root(root: Path) -> tuple[str, str]:
    import shutil
    relatives = (
        "scripts/msae_independent_measurement_v3.py",
        "scripts/msae_measurement_v2.py",
        "scripts/run_msae_independent_calibration_v3.py",
        "scripts/launch_msae_independent_calibration_v3.sh",
        "scripts/run_msae_independent_calibration_v3_gen4.py",
        "scripts/msae_independent_measurement_v3_post_m2_gen4.py",
        "scripts/msae_independent_measurement_v3_post_m2_gen4_runtime.py",
        "scripts/launch_msae_independent_calibration_v3_gen4.sh",
        "docs/rfc-msae-independent-measurement-v3-post-m4-gen4.md",
        "docs/plan-msae-independent-measurement-v3-post-m4-gen4.md",
        "tests/test_msae_independent_measurement_v3_post_m4_gen4.py",
        "reports/adversarial/msae_independent_measurement_v3_post_m2_gen4_plan.md",
        "configs/msae_independent_measurement_v1/protocol.json",
        "data/msae_independent_measurement_v1/calibration_strata.json",
    )
    for relative in relatives:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    implementation = (root /
        "reports/adversarial/msae_independent_measurement_v3_post_m2_gen4_implementation.md")
    implementation.write_text("implementation fixture\n")
    implementation.chmod(0o644)
    return runtime.base.sha_file(
        root / "reports/adversarial/msae_independent_measurement_v3_post_m2_gen4_plan.md"), \
        runtime.base.sha_file(implementation)


def test_generic_protocol_builder_executes_candidate_root_module_not_live_cache(
        tmp_path, monkeypatch):
    root = tmp_path / "candidate"
    _minimal_config_candidate_root(root)
    marker = tmp_path / "rooted-builder-pyc-marker"
    _write_timestamp_valid_malicious_pyc(
        root / "scripts/msae_independent_measurement_v3.py", marker)
    monkeypatch.setattr(
        runtime.base, "build_protocol_config",
        lambda checkpoints: (_ for _ in ()).throw(AssertionError("live builder used")))
    value = runtime._rooted_generic_protocol_config(root, [])
    assert not marker.exists()
    expected_environment = runtime._rooted_generic_environment_sha256(root)
    assert len(value["replay"]["strata"]) == 4
    assert all(row["environment_sha256"] == expected_environment
               for row in value["replay"]["strata"])
    assert all(row["code_sha256"] == runtime.base.sha_file(
        root / "scripts/run_msae_independent_calibration_v3.py")
               for row in value["replay"]["strata"])


def test_real_protocol_config_is_byte_equal_across_two_copied_sparse_roots(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    left_reviews = _minimal_config_candidate_root(left)
    right_reviews = _minimal_config_candidate_root(right)
    assert left_reviews == right_reviews
    left_value = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=left_reviews[0],
        implementation_review_sha256=left_reviews[1], root=left)
    right_value = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=right_reviews[0],
        implementation_review_sha256=right_reviews[1], root=right)
    assert runtime.base.canonical_bytes(left_value) == runtime.base.canonical_bytes(right_value)
    for row in left_value["replay"]["strata"]:
        assert row["code_sha256"] == runtime.base.sha_file(
            left / "scripts/run_msae_independent_calibration_v3_gen4.py")
        assert row["environment_sha256"] == left_value[
            "post_m2_runtime"]["environment_derivation"]["canonical_environment_sha256"]


def test_protocol_config_adapter_is_root_independent_and_projects_generic_schema(
        tmp_path, monkeypatch):
    from msae_measurement_remediation_v1 import validate_draft_config
    left = tmp_path / "left"; right = tmp_path / "right"
    left_reviews = _minimal_config_candidate_root(left)
    right_reviews = _minimal_config_candidate_root(right)
    assert left_reviews == right_reviews
    template = runtime.base.read_json(runtime.V3_CONFIG / "protocol.json")

    def fake_build(checkpoints, candidate_root):
        value = copy.deepcopy(template)
        for row in value["replay"]["strata"]:
            row["code_sha256"] = runtime.base.sha_file(
                candidate_root / "scripts/run_msae_independent_calibration_v3.py")
            row["environment_sha256"] = runtime._rooted_generic_environment_sha256(
                candidate_root)
        return value

    monkeypatch.setattr(runtime, "_rooted_generic_protocol_config",
                        lambda root, checkpoints: fake_build(checkpoints, root))
    successor = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=left_reviews[0],
        implementation_review_sha256=left_reviews[1], root=left)
    rebuilt = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=right_reviews[0],
        implementation_review_sha256=right_reviews[1], root=right)
    assert runtime.base.canonical_bytes(successor) == runtime.base.canonical_bytes(rebuilt)
    derivation = successor["post_m2_runtime"]["environment_derivation"]
    assert "candidate_root_generic_environment_sha256" not in derivation
    assert all(row["code_sha256"] == runtime.base.sha_file(
        left / "scripts/run_msae_independent_calibration_v3_gen4.py")
               for row in successor["replay"]["strata"])
    assert all(row["environment_sha256"] == derivation["canonical_environment_sha256"]
               for row in successor["replay"]["strata"])
    generic = runtime.generic_config_projection(successor)
    assert set(generic) == set(runtime.GENERIC_CONFIG_KEYS)
    assert not set(runtime.SUCCESSOR_CONFIG_KEYS) & set(generic)
    raw = runtime.base.canonical_bytes(generic)
    assert validate_draft_config(raw, runtime.base.sha_bytes(raw))["status"] == "ready"
    with pytest.raises(ValueError, match="successor config key mismatch"):
        runtime.generic_config_projection({**successor, "unreviewed": True})


def test_protocol_config_adapter_rejects_wrong_code_or_environment_precondition(
        tmp_path, monkeypatch):
    root = tmp_path / "candidate"
    reviews = _minimal_config_candidate_root(root)
    template = runtime.base.read_json(runtime.V3_CONFIG / "protocol.json")
    for field in ("code_sha256", "environment_sha256"):
        def fake_build(checkpoints, candidate_root, field=field):
            value = copy.deepcopy(template)
            for row in value["replay"]["strata"]:
                row["code_sha256"] = runtime.base.sha_file(
                    candidate_root / "scripts/run_msae_independent_calibration_v3.py")
                row["environment_sha256"] = runtime._rooted_generic_environment_sha256(
                    candidate_root)
            value["replay"]["strata"][0][field] = "f" * 64
            return value
        monkeypatch.setattr(runtime, "_rooted_generic_protocol_config",
                            lambda root, checkpoints, fake_build=fake_build:
                            fake_build(checkpoints, root))
        with pytest.raises(ValueError, match="substitution precondition"):
            runtime._protocol_config_payload(
                [], runtime.M2_REVIEWED_COMPLETION_SHA256,
                plan_review_sha256=reviews[0], implementation_review_sha256=reviews[1],
                root=root)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra"])
def test_protocol_config_adapter_rejects_missing_duplicate_or_extra_strata(
        tmp_path, monkeypatch, mutation):
    root = tmp_path / "candidate"
    reviews = _minimal_config_candidate_root(root)
    template = runtime.base.read_json(runtime.V3_CONFIG / "protocol.json")

    def fake_build(checkpoints, candidate_root):
        value = copy.deepcopy(template)
        for row in value["replay"]["strata"]:
            row["code_sha256"] = runtime.base.sha_file(
                candidate_root / "scripts/run_msae_independent_calibration_v3.py")
            row["environment_sha256"] = runtime._rooted_generic_environment_sha256(
                candidate_root)
        if mutation == "missing":
            value["replay"]["strata"].pop()
        elif mutation == "duplicate":
            value["replay"]["strata"][-1] = copy.deepcopy(
                value["replay"]["strata"][0])
        else:
            value["replay"]["strata"].append(copy.deepcopy(
                value["replay"]["strata"][0]))
        return value

    monkeypatch.setattr(runtime, "_rooted_generic_protocol_config",
                        lambda root, checkpoints: fake_build(checkpoints, root))
    with pytest.raises(ValueError, match="stratum dimensions drift"):
        runtime._protocol_config_payload(
            [], runtime.M2_REVIEWED_COMPLETION_SHA256,
            plan_review_sha256=reviews[0], implementation_review_sha256=reviews[1],
            root=root)


def test_environment_derivation_never_falls_back_to_candidate_root_venv(tmp_path):
    candidate = tmp_path / "candidate"
    candidate_python = candidate / ".venv-atlas/bin/python"
    candidate_python.parent.mkdir(parents=True)
    candidate_python.write_bytes(b"not the registered interpreter\n")
    candidate_python.chmod(0o755)
    value = runtime._environment_derivation(candidate_root=candidate)
    registered = str((runtime.ROOT / ".venv-atlas/bin/python").resolve(strict=True))
    assert value["canonical_external_python_realpath"] == registered
    assert value["canonical_external_python_realpath"] != str(candidate_python.resolve())
    assert value["canonical_environment_sha256"] != \
        runtime._rooted_generic_environment_sha256(candidate)


def test_protocol_config_adapter_does_not_normalize_an_unrelated_third_field(
        tmp_path, monkeypatch):
    left = tmp_path / "left"; right = tmp_path / "right"
    left_reviews = _minimal_config_candidate_root(left)
    right_reviews = _minimal_config_candidate_root(right)
    template = runtime.base.read_json(runtime.V3_CONFIG / "protocol.json")

    def fake_build(checkpoints, candidate_root):
        value = copy.deepcopy(template)
        for row in value["replay"]["strata"]:
            row["code_sha256"] = runtime.base.sha_file(
                candidate_root / "scripts/run_msae_independent_calibration_v3.py")
            row["environment_sha256"] = runtime._rooted_generic_environment_sha256(
                candidate_root)
        if candidate_root.name == "right":
            value["replay"]["strata"][0]["input_sha256"] = "f" * 64
        return value

    monkeypatch.setattr(runtime, "_rooted_generic_protocol_config",
                        lambda root, checkpoints: fake_build(checkpoints, root))
    left_value = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=left_reviews[0],
        implementation_review_sha256=left_reviews[1], root=left)
    right_value = runtime._protocol_config_payload(
        [], runtime.M2_REVIEWED_COMPLETION_SHA256,
        plan_review_sha256=right_reviews[0],
        implementation_review_sha256=right_reviews[1], root=right)
    assert left_value["replay"]["strata"][0]["input_sha256"] != \
        right_value["replay"]["strata"][0]["input_sha256"]
    assert runtime.base.canonical_bytes(left_value) != runtime.base.canonical_bytes(right_value)


def test_generic_replay_bundle_changes_only_the_config_binding():
    bundle = {"schema_version": "msae_calibration_replay_bundle_v1",
              "protocol_config_sha256": "a" * 64, "replay_registry_sha256": "b" * 64,
              "source_role": "calibration", "source_revision": "c" * 64,
              "partition": "calibration-public", "observations": {}}
    projected = runtime.generic_replay_bundle(bundle, "d" * 64)
    assert projected == {**bundle, "protocol_config_sha256": "d" * 64}
    with pytest.raises(ValueError, match="replay-bundle key mismatch"):
        runtime.generic_replay_bundle({**bundle, "extra": 1}, "d" * 64)


def test_frozen_plan_review_is_canonical_and_machine_bound():
    value = runtime._plan_review_binding(runtime.FROZEN_PLAN_REVIEW_SHA256)
    assert value["scope"] == "gen4_plan"
    assert value["digests"] == {
        "FAILED_GEN3_PLAN": runtime.FAILED_GEN3_PLAN_SHA256,
        "GEN4_PLAN": runtime.FROZEN_PLAN_SHA256,
    }
    with pytest.raises(ValueError):
        runtime._plan_review_binding("0" * 64)


def test_review_gate_rejects_missing_extra_duplicate_and_wrong_scope_controls(
        tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "ROOT", tmp_path)
    path = tmp_path / "review.md"
    expected = {"PLAN": "a" * 64, "RUNTIME": "b" * 64}

    def install(lines):
        path.write_text("\n".join(lines) + "\n")
        path.chmod(0o644)
        return runtime.base.sha_file(path)

    good = ["VERDICT: SHIP", "REVIEW_SCOPE: implementation",
            "PLAN_SHA256: " + "a" * 64, "RUNTIME_SHA256: " + "b" * 64]
    digest = install(good)
    assert runtime._canonical_review(
        path, digest, scope="implementation", expected_digests=expected)["scope"] == \
        "implementation"
    for lines in (
        good + ["EXTRA_SHA256: " + "c" * 64],
        good + ["PLAN_SHA256: " + "a" * 64],
        [line for line in good if not line.startswith("RUNTIME_SHA256")],
        [line.replace("implementation", "plan") for line in good],
        ["VERDICT: BLOCK", *good],
        ["VERDICT : BLOCK", *good],
        ["VERDICT:\tBLOCK", *good],
        ["REVIEW_SCOPE : plan", *good],
        [" VERDICT: SHIP", *good[1:]],
        [*good, "EXTRA_SHA256: not-a-digest"],
    ):
        digest = install(lines)
        with pytest.raises(ValueError):
            runtime._canonical_review(
                path, digest, scope="implementation", expected_digests=expected)


@pytest.mark.parametrize("defect", [
    "symlink", "hardlink", "mode", "owner", "carriage_return",
    "missing_newline", "invalid_utf8", "stale_control", "wrong_scope",
])
def test_create_once_review_rejects_filesystem_and_canonicality_defects(
        tmp_path, monkeypatch, defect):
    monkeypatch.setattr(runtime, "ROOT", tmp_path)
    expected = {"PLAN": "a" * 64}
    raw = ("VERDICT: SHIP\nREVIEW_SCOPE: implementation\n"
           f"PLAN_SHA256: {expected['PLAN']}\n").encode()
    review = tmp_path / "review.md"
    if defect == "carriage_return":
        raw = raw.replace(b"\n", b"\r\n")
    elif defect == "missing_newline":
        raw = raw.rstrip(b"\n")
    elif defect == "invalid_utf8":
        raw += b"\xff\n"
    elif defect == "stale_control":
        raw = raw.replace(b"a" * 64, b"b" * 64)
    elif defect == "wrong_scope":
        raw = raw.replace(b"implementation", b"post_m3")
    if defect == "symlink":
        backing = tmp_path / "backing.md"
        backing.write_bytes(raw); backing.chmod(0o644)
        review.symlink_to(backing)
    else:
        review.write_bytes(raw); review.chmod(0o644)
    if defect == "hardlink":
        os.link(review, tmp_path / "alias.md")
    elif defect == "mode":
        review.chmod(0o600)
    elif defect == "owner":
        actual_uid = review.stat().st_uid
        monkeypatch.setattr(runtime.os, "getuid", lambda: actual_uid + 1)
    supplied = (runtime.base.sha_file(review)
                if defect != "symlink" else "0" * 64)
    with pytest.raises((ValueError, OSError, UnicodeDecodeError)):
        runtime._canonical_review(
            review, supplied, scope="implementation", expected_digests=expected)


def test_gen3_review_namespace_rejects_undeclared_prefixed_sibling(
        tmp_path, monkeypatch):
    root = tmp_path / "reviews"; root.mkdir()
    names = {
        "plan": "msae_independent_measurement_v3_post_m2_gen4_plan.md",
        "implementation":
            "msae_independent_measurement_v3_post_m2_gen4_implementation.md",
        "post": "msae_independent_measurement_v3_post_m2_gen4_post_m3.md",
        "prescore": "msae_independent_measurement_v3_post_m2_gen4_prescore.md",
    }
    for name in (names["plan"], names["implementation"]):
        (root / name).write_text("review\n")
    monkeypatch.setattr(runtime, "PLAN_REVIEW", root / names["plan"])
    monkeypatch.setattr(runtime, "IMPLEMENTATION_REVIEW", root / names["implementation"])
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", root / names["post"])
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", root / names["prescore"])
    runtime._validate_gen3_review_namespace("implementation")
    (root / "msae_independent_measurement_v3_post_m2_gen4_backup.md").write_text(
        "unexpected\n")
    with pytest.raises(ValueError, match="review namespace drift"):
        runtime._validate_gen3_review_namespace("implementation")


def test_gen2_failure_payload_records_only_independently_reproduced_claims():
    before = runtime.GEN2_FAILURE_PATH.exists()
    value = runtime._gen2_failure_payload()
    assert runtime.GEN2_FAILURE_PATH.exists() is before
    assert value["historical_failure"]["evidence_class"] == "operator_attested"
    assert value["historical_failure"]["full_original_transcript_available"] is False
    reproduction = value["independent_root_cause_reproduction"]
    assert reproduction["differing_field_count"] == 4
    assert reproduction["differing_json_pointers"] == [
        f"/replay/strata/{index}/environment_sha256" for index in range(4)]
    assert reproduction["all_other_generic_fields_unchanged"] is True
    assert [row["pointer"] for row in reproduction["field_differences"]] == \
        reproduction["differing_json_pointers"]
    assert all(row["live"] == reproduction["live_environment_sha256"]
               and row["candidate"] == reproduction["candidate_root_environment_sha256"]
               for row in reproduction["field_differences"])
    assert value["stage_a"] == "not_created" and value["model_gpu_tmux"] == "not_run"


def test_gen2_failure_record_create_verify_substitution_and_extra_child(
        tmp_path, monkeypatch):
    parent = tmp_path / "gen2"; parent.mkdir(mode=0o700)
    path = parent / "m4_failure.json"
    monkeypatch.setattr(runtime, "GEN2_FAILURE_PATH", path)
    payload = {"schema_version": "failure", "status": "failed"}
    runtime._preserve_gen2_failure_record(payload)
    assert path.read_bytes() == runtime.base.canonical_bytes(payload)
    runtime._preserve_gen2_failure_record(payload)
    path.write_bytes(runtime.base.canonical_bytes({**payload, "status": "substituted"}))
    with pytest.raises(ValueError, match="failure record drift"):
        runtime._preserve_gen2_failure_record(payload)
    path.write_bytes(runtime.base.canonical_bytes(payload))
    (parent / "extra.json").write_text("{}\n")
    with pytest.raises(ValueError, match="directory projection drift"):
        runtime._preserve_gen2_failure_record(payload)


def test_closure_registry_contains_every_gen3_review_and_failure_input():
    required = {
        runtime.PLAN_PATH.relative_to(runtime.ROOT).as_posix(),
        runtime.PLAN_REVIEW.relative_to(runtime.ROOT).as_posix(),
        runtime.IMPLEMENTATION_REVIEW.relative_to(runtime.ROOT).as_posix(),
        runtime.POST_M3_REVIEW.relative_to(runtime.ROOT).as_posix(),
        runtime.GEN2_FAILURE_PATH.relative_to(runtime.ROOT).as_posix(),
        runtime.continuation.CONTROLLER_PATH.relative_to(runtime.ROOT).as_posix(),
        runtime.RUNTIME.relative_to(runtime.ROOT).as_posix(),
        runtime.RUNNER.relative_to(runtime.ROOT).as_posix(),
        runtime.LAUNCHER.relative_to(runtime.ROOT).as_posix(),
        runtime.RUNTIME_RFC.relative_to(runtime.ROOT).as_posix(),
        runtime.RUNTIME_TEST.relative_to(runtime.ROOT).as_posix(),
    }
    assert required <= set(runtime._candidate_relatives(include_m4=True))


def test_rooted_closure_extension_receives_only_candidate_root_paths(tmp_path, monkeypatch):
    observed = []

    def fake_extend(payload, paths):
        observed.extend(paths)
        return {**payload, "entries": [
            {"path": path.relative_to(tmp_path).as_posix()} for path in paths]}

    monkeypatch.setattr(runtime.continuation, "extend_closure_payload", fake_extend)
    original_root = runtime.base.ROOT
    result = runtime._extend_rooted_closure({"entries": []}, root=tmp_path)
    assert observed and all(path.is_relative_to(tmp_path) for path in observed)
    assert runtime.base.ROOT == original_root
    assert len(result["entries"]) == len(observed)


def test_rooted_closure_extension_is_byte_equal_across_two_real_sparse_roots(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    relatives = {
        runtime.PLAN_PATH.relative_to(runtime.ROOT),
        runtime.PLAN_REVIEW.relative_to(runtime.ROOT),
        runtime.IMPLEMENTATION_REVIEW.relative_to(runtime.ROOT),
        runtime.POST_M3_REVIEW.relative_to(runtime.ROOT),
        runtime.continuation.CONTROLLER_PATH.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTROLLER_PATH.relative_to(runtime.ROOT),
        runtime.RUNTIME.relative_to(runtime.ROOT),
        runtime.RUNNER.relative_to(runtime.ROOT),
        runtime.LAUNCHER.relative_to(runtime.ROOT),
        runtime.RUNTIME_RFC.relative_to(runtime.ROOT),
        runtime.RUNTIME_TEST.relative_to(runtime.ROOT),
        runtime.GEN2_FAILURE_PATH.relative_to(runtime.ROOT),
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "protocol.json",
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "authorization_commitment.json",
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "ed25519_public.pem",
        runtime.CPU_NO_MODEL_TRACE.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTINUATION_RFC.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTINUATION_TEST.relative_to(runtime.ROOT),
        runtime.immutable_continuation.M1_COMPLETION_PATH.relative_to(runtime.ROOT),
    }
    for root in (left, right):
        for relative in relatives:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((relative.as_posix() + "\n").encode())
            target.chmod(0o644)
    left_value = runtime._extend_rooted_closure({"entries": []}, root=left)
    right_value = runtime._extend_rooted_closure({"entries": []}, root=right)
    assert runtime.base.canonical_bytes(left_value) == runtime.base.canonical_bytes(right_value)
    assert all(not Path(row["path"]).is_absolute() for row in left_value["entries"])


def test_config_closure_environment_binding_rejects_missing_and_drifted_python(
        tmp_path, monkeypatch):
    runner = tmp_path / runtime.RUNNER.relative_to(runtime.ROOT)
    runner.parent.mkdir(parents=True)
    runner.write_text("runner\n"); runner.chmod(0o644)
    derivation = runtime._environment_derivation(candidate_root=tmp_path)
    config = {"post_m2_runtime": {"environment_derivation": derivation},
              "replay": {"strata": [
                  {"stratum_id": stratum,
                   "code_sha256": runtime.base.sha_file(runner),
                   "environment_sha256": derivation["canonical_environment_sha256"]}
                  for stratum in runtime.EXPECTED_REPLAY_STRATUM_IDS]}}
    python_row = {
        "path": derivation["canonical_external_python_realpath"],
        "size": derivation["canonical_external_python_size"],
        "mode": derivation["canonical_external_python_mode"],
        "sha256": derivation["canonical_external_python_sha256"], "ldd": [],
    }
    runtime._validate_config_closure_environment(
        config, derivation, [python_row],
        python_executable=derivation["canonical_external_python_realpath"], root=tmp_path)
    for defective in ([], [{**python_row, "size": python_row["size"] + 1}],
                      [{**python_row, "path": "/different/python"}]):
        with pytest.raises(ValueError, match="external Python"):
            runtime._validate_config_closure_environment(
                config, derivation, defective,
                python_executable=derivation["canonical_external_python_realpath"],
                root=tmp_path)
    with pytest.raises(ValueError, match="derivation does not reproduce"):
        runtime._validate_config_closure_environment(
            {**config, "post_m2_runtime": {"environment_derivation": {
                **derivation, "canonical_environment_sha256": "f" * 64}}},
            derivation, [python_row],
            python_executable=derivation["canonical_external_python_realpath"], root=tmp_path)


def test_post_m3_review_binds_every_realized_directory_and_downstream_absence(
        tmp_path, monkeypatch):
    implementation = tmp_path / "implementation.md"
    implementation.write_text("implementation\n"); implementation.chmod(0o644)
    subject = {
        "config_entries": [
            {"path": f"config/{name}", "sha256": chr(97 + index) * 64}
            for index, name in enumerate((
                "protocol.json", "cpu_no_model_public_entry_trace.json",
                "authorization_commitment.json", "ed25519_public.pem"))],
        "private_key_lstat": {"inode": 1, "content_read_for_this_binding": False},
        "directory_bindings": {
            name: {"path": name, "inode": index}
            for index, name in enumerate(
                ("config", "provenance", "m4_data", "state", "nonce"), start=1)},
        "gen2_failure_entry": {"sha256": "e" * 64},
        "gen3_terminal_entry": {"sha256": "f" * 64},
        "setup_manifest_entry": {"sha256": "1" * 64},
        "downstream_absence_sha256": "f" * 64,
    }
    captured = {}

    def fake_review(path, supplied, *, scope, expected_digests):
        captured.update(expected_digests)
        return {"sha256": supplied, "scope": scope}

    monkeypatch.setattr(runtime, "_post_m3_state_binding", lambda **kwargs: subject)
    monkeypatch.setattr(runtime, "_canonical_review", fake_review)
    monkeypatch.setattr(runtime, "IMPLEMENTATION_REVIEW", implementation)
    result = runtime.verify_post_m3_review("9" * 64)
    assert result["review"]["scope"] == "gen4_post_m3"
    assert set(captured) == {
        "GEN4_IMPLEMENTATION_REVIEW", "POST_M3_SUBJECT", "GEN4_PROTOCOL",
        "GEN4_AUTHORIZATION_COMMITMENT", "GEN4_PUBLIC_KEY", "GEN4_CPU_TRACE",
        "GEN4_SETUP_MANIFEST", "GEN3_TERMINAL", "GEN2_M4_FAILURE",
        "M2_COMPLETION",
    }
    assert captured["GEN2_M4_FAILURE"] == "e" * 64


def test_post_m3_subject_uses_lstat_only_private_key_verification(monkeypatch):
    calls = []
    monkeypatch.setattr(runtime, "_validate_gen3_review_namespace", lambda phase: None)
    monkeypatch.setattr(runtime, "_validate_gen2_terminal_namespace", lambda **kwargs: None)
    monkeypatch.setattr(
        runtime, "_verify_existing_authorization_state",
        lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(
        runtime, "_verify_live_cpu_no_model_trace",
        lambda: (_ for _ in ()).throw(RuntimeError("stop after authorization state")))
    with pytest.raises(RuntimeError, match="stop after authorization state"):
        runtime._post_m3_state_binding()
    assert calls == [{"verify_private_content": False}]


def test_post_m3_absence_patterns_cover_immutable_gen2_actual_prefixes():
    patterns = set(runtime._post_m3_forbidden_tmp_patterns())
    assert {
        "msae_independent_measurement_v3_*.prescore.check.json",
        "msae_independent_measurement_v3_*.prescore.trace.log",
        "msae_independent_measurement_v3_*.sock",
    } <= patterns


def test_quarantine_guard_runs_after_checks_when_guarded_body_raises(monkeypatch):
    rows = [{"path": "sealed", "nlink": 1}]
    calls = []
    def metadata():
        calls.append("lstat")
        return copy.deepcopy(rows)
    @contextlib.contextmanager
    def tripwire():
        state = {"before_lstat": copy.deepcopy(rows),
                 "blocked_content_open_attempts": []}
        yield state
    monkeypatch.setattr(runtime, "_quarantine_metadata_rows", metadata)
    monkeypatch.setattr(runtime.base, "quarantine_open_tripwire", tripwire)
    with pytest.raises(RuntimeError, match="guarded failure"):
        with runtime.quarantine_guard():
            raise RuntimeError("guarded failure")
    assert calls == ["lstat", "lstat"]


def test_private_key_content_is_confined_to_explicit_setup_and_signer_paths():
    state_source = inspect.getsource(runtime._verify_existing_authorization_state)
    tree_source = inspect.getsource(runtime._validate_tree_authorization)
    verify_source = inspect.getsource(runtime.verify_authorization)
    assert "if verify_private_content:" in state_source
    assert runtime._verify_existing_authorization_state.__kwdefaults__ == {
        "verify_private_content": False}
    assert "_regular_bytes(ACTIVE_PRIVATE_KEY" not in tree_source
    assert "verify_private_content=True" not in verify_source


def test_private_key_lstat_binding_rejects_same_inode_content_rewrite(tmp_path):
    key = tmp_path / "key.pem"; key.write_bytes(b"first-key\n"); key.chmod(0o600)
    st = key.lstat()
    binding = {"path": str(key), "device": st.st_dev, "inode": st.st_ino,
               "uid": st.st_uid, "nlink": st.st_nlink,
               "mode": stat.S_IMODE(st.st_mode), "size": st.st_size,
               "mtime_ns": st.st_mtime_ns, "ctime_ns": st.st_ctime_ns}
    runtime._validate_private_key_lstat_binding(key, binding)
    time.sleep(0.002)
    key.write_bytes(b"other-key\n")
    with pytest.raises(ValueError, match="private key binding drift"):
        runtime._validate_private_key_lstat_binding(key, binding)


def test_authorization_commitment_rejects_schema_and_lifetime_drift_before_use(
        tmp_path, monkeypatch):
    repo = tmp_path / "repo"; (repo / "configs").mkdir(parents=True)
    reviews = repo / "reports/adversarial"; reviews.mkdir(parents=True)
    plan = repo / "docs/plan.md"; plan.parent.mkdir(parents=True); plan.write_text("plan\n")
    plan_review = reviews / "plan.md"; plan_review.write_text("plan review\n")
    implementation = reviews / "implementation.md"; implementation.write_text(
        "implementation\n")
    for path in (plan, plan_review, implementation):
        path.chmod(0o644)
    config = repo / "configs/gen3"
    private = tmp_path / "keys/private.pem"
    state = tmp_path / "state/gen3"
    nonce = state / "nonces"
    gpu = tmp_path / "gpu-locks"
    monkeypatch.setattr(runtime, "ROOT", repo)
    monkeypatch.setattr(runtime, "PLAN_PATH", plan)
    monkeypatch.setattr(runtime, "PLAN_REVIEW", plan_review)
    monkeypatch.setattr(runtime, "IMPLEMENTATION_REVIEW", implementation)
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PRIVATE_KEY", private)
    monkeypatch.setattr(runtime, "ACTIVE_STATE", state)
    monkeypatch.setattr(runtime, "ACTIVE_NONCE_DIR", nonce)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", gpu)
    gates = runtime._trace_review_gates(
        repo, runtime.FROZEN_PLAN_REVIEW_SHA256,
        runtime.base.sha_file(implementation))
    runtime._create_active_authorization_state(gates)
    runtime._verify_existing_authorization_state(verify_private_content=True)
    commitment_path = config / "authorization_commitment.json"
    commitment = runtime.base.strict_json_loads(commitment_path.read_text())
    commitment["maximum_lifetime_seconds"] = 1
    commitment_path.write_bytes(runtime.base.canonical_bytes(commitment))
    commitment_path.chmod(0o644)
    with pytest.raises(ValueError, match="commitment semantics drift"):
        runtime._verify_existing_authorization_state(verify_private_content=False)


def test_regular_candidate_entries_bind_owner_and_link_count(tmp_path, monkeypatch):
    item = tmp_path / "item"; item.write_text("payload\n"); item.chmod(0o644)
    entry = runtime._regular_entry(item, root=tmp_path)
    assert entry["uid"] == os.getuid() and entry["nlink"] == 1
    monkeypatch.setattr(runtime, "ROOT", tmp_path)
    assert runtime._verify_manifest_entry(entry)["result"] == "match"
    with pytest.raises(ValueError, match="candidate entry drift"):
        runtime._verify_manifest_entry({**entry, "uid": entry["uid"] + 1})
    alias = tmp_path / "alias"; os.link(item, alias)
    with pytest.raises(ValueError, match="identity drift"):
        runtime._regular_entry(item, root=tmp_path)


def test_transition_cli_requires_both_review_gates_before_dispatch():
    python = str(ROOT / ".venv-atlas/bin/python")
    controller = str(runtime.continuation.CONTROLLER_PATH)
    guarded = [runtime.ACTIVE_CONFIG, runtime.ACTIVE_PROV, runtime.ACTIVE_M4_DATA,
               runtime.ACTIVE_RUN_ROOT, *(runtime.ROOT / item for item in runtime.M4_NEW)]
    before = [(path.exists(), path.is_symlink()) for path in guarded]
    setup = subprocess.run(
        [python, "-S", "-B", "-I", controller, "setup-m3-gen4",
         "--reviewed-m2-sha256", runtime.M2_REVIEWED_COMPLETION_SHA256],
        text=True, capture_output=True)
    assert setup.returncode != 0
    assert "noncanonical gen4 command shape" in setup.stderr
    m4 = subprocess.run(
        [python, "-S", "-B", "-I", controller, "build-m4-gen4"],
        text=True, capture_output=True)
    assert m4.returncode != 0
    assert "noncanonical gen4 command shape" in m4.stderr
    assert [(path.exists(), path.is_symlink()) for path in guarded] == before


def test_m2_semantic_closure_matches_installed_outputs():
    assert runtime._validate_m2_semantics() == {
        "label_rows": 1491748, "role_task_cells": 68, "map_entries": 34000,
        "finite_draws_per_cell": 500, "support_status": "eligible",
        "finite_pass_status": "eligible",
        "correction_denominators": {"raw_selected": [290192, 36],
                                    "retained_after_cap": [89600, 11],
                                    "tokenizable": [286938, 20]}}


def test_persisted_m2_completion_round_trip_is_verifiable():
    digest = "e593a6283aa5468ddbee1cc755dbe60c4ee503375a0cbce44c52614dd232d737"
    with runtime.base.quarantine_open_tripwire() as state:
        assert runtime.verify_m2_completion(digest)["status"] == \
            "m2_support_and_maps_eligible_ready_for_independent_review_pin"
    assert state["blocked_content_open_attempts"] == []


def test_m3_rejects_every_nonreviewed_m2_digest_before_writing():
    with pytest.raises(ValueError, match="independently reviewed M2"):
        runtime.setup_m3_gen4("0" * 64, "a" * 64, "b" * 64,
                              "c" * 64, "d" * 64)


def test_failed_m3_preflight_pins_match_the_preserved_bytes():
    assert runtime.base.sha_file(runtime.V3_CONFIG / "protocol.json") == runtime.FAILED_M3_CONFIG_SHA256
    assert runtime.base.sha_file(runtime.V3_CONFIG / "authorization_commitment.json") == \
        runtime.FAILED_M3_COMMITMENT_SHA256
    assert runtime.base.sha_file(runtime.V3_CONFIG / "ed25519_public.pem") == \
        runtime.FAILED_M3_PUBLIC_SHA256


def test_m3_existing_protocol_rejects_symlink_before_acceptance(tmp_path):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    private = tmp_path / "private"; private.write_bytes(b"key")
    for name in ("ed25519_public.pem", "authorization_commitment.json"):
        (config / name).write_bytes(b"x")
    cpu_trace = config / "cpu_no_model_public_entry_trace.json"
    cpu_trace.write_bytes(runtime.base.canonical_bytes({})); cpu_trace.chmod(0o644)
    backing = tmp_path / "protocol.json"; backing.write_bytes(runtime.base.canonical_bytes({"x": 1}))
    (config / "protocol.json").symlink_to(backing)
    with pytest.raises(OSError):
        runtime._regular_bytes(config / "protocol.json", mode=0o644)


def test_setup_preflight_rejects_preplanted_namespace_before_any_write(
        tmp_path, monkeypatch):
    config = tmp_path / "config"
    private = tmp_path / "private.pem"
    state = tmp_path / "state"
    provenance = tmp_path / "provenance"; provenance.mkdir(mode=0o700)
    (provenance / "planted.json").write_text("{}\n")
    m4_data = tmp_path / "m4-data"
    post_review = tmp_path / "post-review.md"
    prescore_review = tmp_path / "prescore-review.md"
    run = tmp_path / "run"
    transaction = tmp_path / "transaction"
    primary = tmp_path / "primary"; rebuild = tmp_path / "rebuild"
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PRIVATE_KEY", private)
    monkeypatch.setattr(runtime, "ACTIVE_STATE", state)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", provenance)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", m4_data)
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", post_review)
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", prescore_review)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    monkeypatch.setattr(runtime, "M4_TRANSACTION", transaction)
    monkeypatch.setattr(runtime, "M4_PRIMARY", primary)
    monkeypatch.setattr(runtime, "M4_REBUILD", rebuild)
    monkeypatch.setattr(runtime, "M4_NEW", tuple())
    monkeypatch.setattr(runtime, "_validate_gen3_review_namespace", lambda phase: None)
    with pytest.raises(ValueError, match="projection|undeclared|without its journal"):
        runtime._validate_setup_namespace_preconditions({"status": "failed"})
    assert not config.exists() and not private.exists()


def test_setup_existing_state_requires_private_agreement_before_first_write(
        tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    gen2 = tmp_path / "gen2"; gen2.mkdir(mode=0o700)
    failure = gen2 / "m4_failure.json"
    predicted = {"status": "failed"}
    failure.write_bytes(runtime.base.canonical_bytes(predicted)); failure.chmod(0o644)
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "GEN2_FAILURE_PATH", failure)
    monkeypatch.setattr(runtime, "M4_NEW", tuple())
    monkeypatch.setattr(runtime, "M4_TRANSACTION", tmp_path / "transaction")
    monkeypatch.setattr(runtime, "M4_PRIMARY", tmp_path / "primary")
    monkeypatch.setattr(runtime, "M4_REBUILD", tmp_path / "rebuild")
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", tmp_path / "post-review")
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", tmp_path / "prescore-review")
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", tmp_path / "run")
    monkeypatch.setattr(runtime, "_validate_gen3_review_namespace", lambda phase: None)
    calls = []
    def reject(**kwargs):
        calls.append(kwargs)
        raise ValueError("private/public key mismatch")
    monkeypatch.setattr(runtime, "_verify_existing_authorization_state", reject)
    with pytest.raises(ValueError, match="ahead of receipt prefix"):
        runtime._validate_setup_namespace_preconditions(predicted)
    assert calls == []
    assert list(config.iterdir()) == []


def test_secure_directory_projection_rejects_permissive_mode(tmp_path):
    directory = tmp_path / "secure"; directory.mkdir(mode=0o700)
    runtime._exact_directory_entries(directory, set(), mode=0o700)
    directory.chmod(0o777)
    with pytest.raises(ValueError, match="invalid projected directory"):
        runtime._exact_directory_entries(directory, set(), mode=0o700)


@pytest.mark.parametrize("line,expected", [
    ('1 openat(AT_FDCWD</repo>, "data/private", O_RDONLY) = 3</repo/data/private>',
     "/repo/data/private"),
    ('2 openat(5</repo/data>, "private", O_RDONLY) = 6</repo/data/private>',
     "/repo/data/private"),
    ('3 open("/repo/data/private", O_RDONLY) = 4</repo/data/private>',
     "/repo/data/private"),
])
def test_trace_parser_resolves_absolute_and_dirfd_opens(line, expected):
    assert expected in runtime._trace_open_candidates(line)
    with pytest.raises(ValueError, match="forbidden content open"):
        runtime.verify_trace_no_forbidden(line, [Path(expected)])


def test_review_verdict_parser_rejects_conflicts_and_duplicate_digest_lines(tmp_path, monkeypatch):
    manifest = {"stage_a_sha256": "a" * 64, "dependency_closure_sha256": "b" * 64}
    check = tmp_path / "check"; check.write_bytes(b"check")
    trace = tmp_path / "trace"; trace.write_bytes(b"trace")
    files = {}
    for name in ("implementation", "post_m3", "protocol", "status",
                 "endpoint_registry.json", "environment_allowlist.json", "checker"):
        path = tmp_path / name; path.write_bytes((name + "\n").encode()); files[name] = path
    active_config = tmp_path / "config"; active_config.mkdir()
    active_prov = tmp_path / "prov"; active_prov.mkdir()
    active_data = tmp_path / "data"; active_data.mkdir()
    (active_config / "protocol.json").write_bytes(files["protocol"].read_bytes())
    (active_prov / "status.json").write_bytes(files["status"].read_bytes())
    (active_data / "endpoint_registry.json").write_bytes(files["endpoint_registry.json"].read_bytes())
    (active_data / "environment_allowlist.json").write_bytes(files["environment_allowlist.json"].read_bytes())
    monkeypatch.setattr(runtime, "IMPLEMENTATION_REVIEW", files["implementation"])
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", files["post_m3"])
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", active_config)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", active_prov)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", active_data)
    monkeypatch.setattr(runtime, "RUNTIME", files["checker"])
    monkeypatch.setattr(runtime, "_prescore_evidence_paths", lambda digest: (check, trace))
    good = "\n".join(["VERDICT: SHIP", "REVIEW_SCOPE: gen4_prescore",
                       "GEN4_IMPLEMENTATION_REVIEW_SHA256: " + runtime.base.sha_file(files["implementation"]),
                       "GEN4_POST_M3_REVIEW_SHA256: " + runtime.base.sha_file(files["post_m3"]),
                       "GEN4_PROTOCOL_SHA256: " + runtime.base.sha_file(active_config / "protocol.json"),
                       "GEN4_STAGE_A_SHA256: " + "a" * 64,
                       "GEN4_STATUS_SHA256: " + runtime.base.sha_file(active_prov / "status.json"),
                       "GEN4_CANDIDATE_MANIFEST_SHA256: " + "c" * 64,
                       "GEN4_DEPENDENCY_CLOSURE_SHA256: " + "b" * 64,
                       "GEN4_ENDPOINT_REGISTRY_SHA256: " + runtime.base.sha_file(active_data / "endpoint_registry.json"),
                       "GEN4_ENVIRONMENT_ALLOWLIST_SHA256: " + runtime.base.sha_file(active_data / "environment_allowlist.json"),
                       "GEN4_PRESCORE_CHECK_SHA256: " + runtime.base.sha_file(check),
                       "GEN4_PRESCORE_TRACE_SHA256: " + runtime.base.sha_file(trace),
                       "GEN4_PRESCORE_CHECKER_SHA256: " + runtime.base.sha_file(files["checker"]),
                       "SEALED_PAYLOAD_CONTENT_READS: 0"])
    runtime._strict_review_verdict(good, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict("VERDICT: BLOCK\n" + good, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(good + "\nGEN4_STAGE_A_SHA256: " + "a" * 64, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(good + "\nGEN4_STAGE_A_SHA256: " + "0" * 64, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(good + "\nEXTRA_SHA256: " + "0" * 64, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(good + "\n GEN4_STAGE_A_SHA256: " + "0" * 64, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(" VERDICT: BLOCK\n" + good, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict("VERDICT : BLOCK\n" + good, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict("VERDICT:\tBLOCK\n" + good, manifest, "c" * 64)


def test_prescore_trace_requires_the_exact_typed_check_payload(tmp_path, monkeypatch):
    data = tmp_path / "data"; data.mkdir()
    prov = tmp_path / "prov"; prov.mkdir()
    manifest = {"candidate_tree_sha256": "a" * 64,
                "repository_status": ["? candidate"],
                "repository_status_classification": [],
                "candidate_files": [{"path": "candidate"}],
                "candidate_directories": [], "quarantined_entries": []}
    manifest_path = prov / "prescore_candidate_manifest.json"
    stage_path = prov / "stage_a.json"
    status_path = prov / "status.json"
    closure_path = data / "dependency_closure.json"
    manifest_path.write_bytes(runtime.base.canonical_bytes(manifest))
    stage_path.write_bytes(runtime.base.canonical_bytes({"stage_ready": True}))
    status_path.write_bytes(runtime.base.canonical_bytes({"status": "ready_prescore_review"}))
    closure_path.write_bytes(runtime.base.canonical_bytes({"entries": []}))
    for path in (manifest_path, stage_path, status_path, closure_path):
        path.chmod(0o644)
    manifest_sha = runtime.base.sha_file(manifest_path)
    check, trace = tmp_path / "check.json", tmp_path / "trace.log"
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", data)
    monkeypatch.setattr(runtime, "_prescore_evidence_paths", lambda digest: (check, trace))
    monkeypatch.setattr(runtime, "_expected_live_candidate_paths", lambda: {"candidate"})
    monkeypatch.setattr(runtime, "_directory_entries", lambda *a, **k: [])
    monkeypatch.setattr(runtime, "candidate_manifest_payload", lambda *a, **k: manifest)
    monkeypatch.setattr(runtime, "_verify_manifest_entry", lambda row: {
        "path": "candidate", "verification_action": "content_rehash", "result": "match"})
    monkeypatch.setattr(runtime, "_quarantine_manifest_results", lambda value: [])
    monkeypatch.setattr(runtime, "_protected_baseline_results", lambda: {"result": "match"})
    expected = {
        "schema_version": "msae_v3_prescore_check_v3", "protocol_id": runtime.PROTOCOL,
        "phase": "prescore", "manifest_sha256": manifest_sha,
        "checker_code_sha256": "b" * 64, "candidate_tree_sha256": "a" * 64,
        "dependency_closure_sha256": runtime.base.sha_file(closure_path),
        "stage_a_sha256": runtime.base.sha_file(stage_path), "m4_status_sha256": "c" * 64,
        "candidate_file_results": [{"path": "candidate", "result": "match"}],
        "candidate_directory_results": [], "quarantined_metadata_results": [],
        "protected_baseline_results": {"result": "match"},
        "repository_status_projection": manifest["repository_status"],
        "repository_status_classification": [],
        "repository_status_sha256": runtime.base.sha_bytes(
            runtime.base.canonical_bytes(manifest["repository_status"])),
        "candidate_file_count": 1, "candidate_directory_count": 0,
        "quarantined_entry_count": 0, "sealed_payload_content_reads": 0, "eligible": True,
    }
    monkeypatch.setattr(runtime, "_prescore_check_payload", lambda **kwargs: expected)
    check.write_bytes(runtime.base.canonical_bytes(expected)); check.chmod(0o600)
    required = [runtime.continuation.CONTROLLER_PATH, runtime.RUNTIME, manifest_path,
                stage_path, closure_path]
    lines = [f'{i} open("{path.resolve()}", O_RDONLY) = {i + 3}<{path.resolve()}>'
             for i, path in enumerate(required)]
    lines *= 2
    trace.write_text("\n".join(lines) + "\n" + ("#" * 1024) + "\n")
    trace.chmod(0o600)
    assert runtime.verify_prescore_trace(manifest_path, check, trace)["eligible"] is True
    for key in list(expected):
        mutated = copy.deepcopy(expected)
        mutated[key] = None
        check.write_bytes(runtime.base.canonical_bytes(mutated)); check.chmod(0o600)
        with pytest.raises(ValueError, match="prescore check output mismatch"):
            runtime.verify_prescore_trace(manifest_path, check, trace)
    mutated = {**expected, "unexpected": True}
    check.write_bytes(runtime.base.canonical_bytes(mutated)); check.chmod(0o600)
    with pytest.raises(ValueError, match="prescore check output mismatch"):
        runtime.verify_prescore_trace(manifest_path, check, trace)


def test_ldd_inventory_rejects_missing_dependency(monkeypatch, tmp_path):
    executable = tmp_path / "x"; executable.write_bytes(b"\x7fELF")
    monkeypatch.setattr(runtime.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 0, "libmissing.so => not found\n", ""))
    with pytest.raises(ValueError, match="unresolved ldd dependency"):
        runtime._ldd_inventory(executable)


def test_ldd_inventory_uses_closed_environment(monkeypatch, tmp_path):
    executable = tmp_path / "x"; executable.write_bytes(b"#!x")
    observed = {}
    def fake(*args, **kwargs):
        observed.update(kwargs["env"])
        return subprocess.CompletedProcess(args[0], 0, "statically linked\n", "")
    monkeypatch.setenv("LD_PRELOAD", "/tmp/escape.so")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/escape")
    monkeypatch.setattr(runtime.subprocess, "run", fake)
    assert runtime._ldd_inventory(executable) == []
    assert observed == runtime.FROZEN_BASE_PROCESS_ENVIRONMENT


def test_recursive_static_closure_rejects_planted_surface_escapes(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    runner = tmp_path / "scripts/run_msae_independent_calibration_v3_gen4.py"
    planted = [
        'subprocess.run(["/bin/false"])',
        'Path("/etc/passwd").read_text()',
        'import ctypes; ctypes.CDLL("/tmp/escape.so")',
        'import socket; socket.socket(socket.AF_INET)',
        'subprocess.run("echo escape", shell=True)',
        'getattr(subprocess, "run")(["/bin/false"])',
        'import subprocess as sp; sp.run(["/bin/false"])',
        'alias = subprocess.run; alias(["/bin/false"])',
    ]
    for statement in planted:
        original = runner.read_text()
        runner.write_text(original + "\n" + statement + "\n")
        with pytest.raises(ValueError):
            runtime._static_closure_analysis(root=tmp_path)
        runner.write_text(original)


def test_static_closure_semantically_rejects_literal_and_unregistered_dynamic_file_sites(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    runner = tmp_path / "scripts/run_msae_independent_calibration_v3_gen4.py"
    original = runner.read_text()
    runner.write_text(original + '\nPath("/etc/passwd").read_text()\n')
    with pytest.raises(ValueError, match="absolute file literal"):
        runtime._static_closure_analysis(root=tmp_path)
    runner.write_text(original + '\ndef planted_dynamic_file(p): return Path(p).read_text()\n')
    # Even treating both aggregate syntax hashes as already reviewed cannot
    # authorize a new site absent from the per-site binding registry.
    with pytest.raises(ValueError, match="lacks a reviewed typed-field binding"):
        runtime._static_closure_analysis(root=tmp_path)


def test_static_closure_rejects_indirect_helper_keyword_and_assignment_path_bypasses(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    runner = tmp_path / "scripts/run_msae_independent_calibration_v3_gen4.py"
    original = runner.read_text()
    for planted in (
        '\nprotocol.read_json(Path("/etc/passwd"))\n',
        '\nprotocol.read_json(path=Path("/etc/passwd"))\n',
    ):
        runner.write_text(original + planted)
        with pytest.raises(ValueError, match="absolute file literal"):
            runtime._static_closure_analysis(root=tmp_path)
    # Rebind an already-approved sink variable without changing the sink call
    # or either aggregate surface set. Assignment-origin checking must catch it.
    runner.write_text(original.replace(
        '    config_raw = config_path.read_bytes()\n',
        '    config_path = Path("/etc/passwd")\n    config_raw = config_path.read_bytes()\n'))
    with pytest.raises(ValueError, match="assigned literal outside"):
        runtime._static_closure_analysis(root=tmp_path)
    runner.write_text(original.replace(
        '    config_path = runtime.ACTIVE_CONFIG / "protocol.json"\n',
        '    config_path = Path("/etc") / "passwd"\n'))
    with pytest.raises(ValueError, match="assigned literal outside"):
        runtime._static_closure_analysis(root=tmp_path)


def test_static_network_closure_includes_bound_unix_socket_methods():
    operations = {row["operation"] for row in runtime._static_closure_analysis()["surface_calls"]
                  if row["category"] == "network"}
    assert {"sock.connect", "server.bind", "server.listen", "server.accept",
            "connection.sendmsg", "connection.getsockopt"} <= operations


def test_static_dynamic_imports_have_exact_site_specific_targets(tmp_path):
    import shutil
    value = runtime._static_closure_analysis()
    targets = {tuple(row["finite_mapping"]) for row in value["dynamic_import_mappings"]}
    assert {
        ("scripts/msae_independent_measurement_v3.py",),
        ("scripts/run_msae_independent_calibration_v3.py",),
        ("scripts/run_msae_independent_calibration_v3_gen4.py",),
        ("scripts/msae_measurement_v2.py",),
        ("scripts/msae_measurement_remediation_v1.py",),
    } <= targets
    gen3_dynamic = [row for row in value["dynamic_import_mappings"]
                    if row["path"].endswith("post_m2_gen4_runtime.py")]
    assert gen3_dynamic and all(
        row["operation"] == "continuation.source_only_module_spec"
        for row in gen3_dynamic)
    policy = value["source_only_local_import_policy"]
    assert policy["bytecode_cache_reads"] is False
    assert policy["default_scripts_directory_search"] is False
    assert policy["ignored_sourceless_or_extension_shadowing"] is False
    assert set(policy["modules"]) == {
        Path(relative).stem for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS}
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    module = tmp_path / "scripts/msae_independent_measurement_v3_post_m2_gen4_runtime.py"
    original = module.read_text()
    module.write_text(original.replace(
        'continuation.source_only_module_spec(module_name, builder_path)',
        'continuation.source_only_module_spec(module_name, candidate_root / '
        '"scripts/run_msae_independent_calibration_v3_gen4.py")', 1))
    with pytest.raises(ValueError, match="dynamic import site lacks an exact mapping"):
        runtime._static_closure_analysis(root=tmp_path)


def test_static_value_flow_ledger_closes_caller_argv_and_helper_return_bypasses(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    module = tmp_path / "scripts/msae_independent_measurement_v3_post_m2_gen4_runtime.py"
    original = module.read_text()
    module.write_text(original.replace(
        'argv = [str(ROOT / ".venv-atlas/bin/python"), "-S", "-B", "-I",\n'
        '            str(continuation.CONTROLLER_PATH), "broker-gen4",',
        'argv = ["/bin/false", "-S", "-B", "-I",\n'
        '            str(continuation.CONTROLLER_PATH), "broker-gen4",', 1))
    with pytest.raises(ValueError, match="local value-flow AST ledger drift"):
        runtime._static_closure_analysis(root=tmp_path)


def test_static_ledger_self_exclusions_are_syntactically_inert(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    module = tmp_path / "scripts/msae_independent_measurement_v3_post_m2_gen4_runtime.py"
    original = module.read_text()
    module.write_text(original.replace(
        f'FROZEN_LOCAL_VALUE_FLOW_AST_SHA256 = "{runtime.FROZEN_LOCAL_VALUE_FLOW_AST_SHA256}"',
        'FROZEN_LOCAL_VALUE_FLOW_AST_SHA256 = (base.launch(), "' +
        runtime.FROZEN_LOCAL_VALUE_FLOW_AST_SHA256 + '")[1]'))
    with pytest.raises(ValueError, match="digest constant is not inert"):
        runtime._static_closure_analysis(root=tmp_path)
    module.write_text(original.replace(
        '    return Path(f"{prefix}.prescore.check.json"), Path(f"{prefix}.prescore.trace.log")',
        '    return Path("/etc/passwd"), Path("/etc/shadow")'))
    with pytest.raises(ValueError, match="local value-flow AST ledger drift"):
        runtime._static_closure_analysis(root=tmp_path)


def test_cpu_no_model_trace_executes_every_public_entry_and_planted_tripwires():
    value = runtime.cpu_no_model_public_entry_trace()
    assert value["status"] == "eligible" and value["model_imports"] == 0
    assert value["entrypoints"] == list(runtime.PUBLIC_EXECUTION_ENTRYPOINTS)
    assert [row["entrypoint"] for row in value["results"]] == list(
        runtime.PUBLIC_EXECUTION_ENTRYPOINTS)
    assert all(row["outcome"] != "prescore_rejected:_SurfaceProbeViolation"
               for row in value["results"])
    assert {"indirect_open", "dynamic_subprocess", "shell_expansion", "bash_command",
            "dlopen_escape", "network_escape"} <= set(value["tripwire_proofs"])
    assert value["finite_file_registry"]["schema_version"] == \
        "msae_v3_finite_file_registry_v1"
    assert value["finite_process_registry"]["schema_version"] == \
        "msae_v3_finite_process_registry_v1"
    process_registry = value["finite_process_registry"]
    declared_process_ids = ({row["id"] for row in process_registry["exact_argv"]} |
                            {row["id"] for row in process_registry["templates"]})
    process_requests = [row for row in value["allowed_requests"]
                        if row["category"] == "process"]
    assert process_requests
    assert all(len(row["registry_entry_ids"]) == 1 for row in process_requests)
    assert all(row["registry_entry_ids"][0] in declared_process_ids
               for row in process_requests)
    assert any(row["registry_entry_ids"] == ["isolated_python_worker_execve"]
               for row in process_requests)


def test_cpu_trace_validator_rejects_process_registry_substitution(monkeypatch):
    gates = {
        "plan_sha256": runtime.FROZEN_PLAN_SHA256,
        "plan_entry": {}, "plan_review_sha256": "a" * 64,
        "plan_review_entry": {}, "implementation_review_sha256": "b" * 64,
        "implementation_review_entry": {},
    }
    value = runtime.cpu_no_model_public_entry_trace(review_gates=gates)
    monkeypatch.setattr(runtime, "_trace_review_gates", lambda *args: gates)
    mutated = copy.deepcopy(value)
    mutated["finite_process_registry"]["templates"][0]["id"] = "forged"
    with pytest.raises(ValueError, match="finite process registry drift"):
        runtime._validate_cpu_no_model_trace(
            mutated, root=ROOT, checkpoints=runtime.checkpoint_registry())


def test_model_snapshot_exact_set_rejects_extra_missing_and_outbound_symlink(tmp_path):
    snapshot = tmp_path / "cache/hub/snapshots/revision"
    snapshot.mkdir(parents=True)
    for name in runtime.EXPECTED_MODEL_SNAPSHOT_NAMES:
        (snapshot / name).write_bytes(name.encode())
    assert len(runtime._model_snapshot_entries(snapshot)) == 5
    (snapshot / "extra.bin").write_bytes(b"x")
    with pytest.raises(ValueError, match="filename set drift"):
        runtime._model_snapshot_entries(snapshot)
    (snapshot / "extra.bin").unlink()
    missing = snapshot / "config.json"; missing.unlink()
    with pytest.raises(ValueError, match="missing"):
        runtime._model_snapshot_entries(snapshot)
    outside = tmp_path / "outside.json"; outside.write_bytes(b"outside")
    missing.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes frozen cache root"):
        runtime._model_snapshot_entries(snapshot)


def test_candidate_projection_contains_every_protected_predecessor_path():
    candidate = set(runtime._candidate_relatives(include_m4=True))
    for name in ("protected_v1_manifest.json", "protected_v2_manifest.json"):
        protected = runtime.base.read_json(runtime.V3_DATA / name)
        assert {row["path"] for row in protected["entries"]} <= candidate


def test_overlay_never_falls_back_to_live_tree(tmp_path):
    with pytest.raises(FileNotFoundError, match="candidate-root input is absent"):
        runtime._overlay("TODO.md", tmp_path)


def test_rooted_generic_stage_builder_does_not_use_live_cached_dependency(tmp_path):
    scripts = tmp_path / "scripts"; scripts.mkdir()
    for name in ("msae_measurement_v2.py", "msae_measurement_remediation_v1.py"):
        source = ROOT / "scripts" / name
        target = scripts / name
        target.write_bytes(source.read_bytes())
        target.chmod(0o700)
    with (scripts / "msae_measurement_v2.py").open("ab") as handle:
        handle.write(b"\n# planted candidate-tree drift\n")
    raw = (ROOT / "configs/msae_measurement_remediation_v1/draft.json").read_bytes()
    with pytest.raises(ValueError, match="dependency digest mismatch"):
        runtime._rooted_generic_build_stage_a(
            tmp_path, raw, runtime.base.sha_bytes(raw), {})


def test_repository_classification_reads_only_explicit_tree(tmp_path):
    data = tmp_path / "data/msae_independent_measurement_v3"; data.mkdir(parents=True)
    for name in ("protected_v1_manifest.json", "protected_v2_manifest.json",
                 "data_baseline_manifest.json"):
        (data / name).write_text('{"entries":[]}\n')
    rows = runtime._classify_repository_status(["? candidate.txt"], {"candidate.txt"}, root=tmp_path)
    assert rows == [{"line": "? candidate.txt", "path_projection": "candidate.txt",
                     "classification": "candidate"}]


def test_repository_status_rejects_unclassified_path(monkeypatch):
    monkeypatch.setattr(runtime.base, "read_json", lambda path: {"entries": []})
    with pytest.raises(ValueError, match="unclassified"):
        runtime._classify_repository_status(["? surprise.txt"], {"candidate.txt"})


def test_generic_transaction_recovers_all_boundaries(tmp_path, monkeypatch):
    root = tmp_path / "txn"
    repo = tmp_path / "repo"
    repo.mkdir()
    relatives = ("a/x.json", "b/y.json", "c/z.json")
    payloads = {relative: (relative + "\n").encode() for relative in relatives}
    for relative in relatives:
        (repo / relative).parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(runtime, "ROOT", repo)
    original = runtime._atomic_publish
    calls = 0

    def interrupted(path, payload, mode=0o644, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected")
        return original(path, payload, mode, **kwargs)

    monkeypatch.setattr(runtime, "_atomic_publish", interrupted)
    with pytest.raises(OSError, match="injected"):
        runtime._install_transaction(root, relatives, payloads, "test")
    monkeypatch.setattr(runtime, "_atomic_publish", original)
    runtime._install_transaction(root, relatives, payloads, "test")
    assert not root.exists()
    assert all((repo / relative).read_bytes() == payloads[relative] for relative in relatives)


def test_transaction_rejects_partial_targets_after_transaction_root_loss(
        tmp_path, monkeypatch):
    repo = tmp_path / "repo"; repo.mkdir()
    txn = tmp_path / "lost-then-recreated-transaction"
    relatives = ("a/x.json", "b/y.json")
    payloads = {relative: (relative + "\n").encode() for relative in relatives}
    first = repo / relatives[0]; first.parent.mkdir(parents=True)
    first.write_bytes(payloads[relatives[0]]); first.chmod(0o644)
    monkeypatch.setattr(runtime, "ROOT", repo)
    with pytest.raises(ValueError, match="transaction missing"):
        runtime._install_transaction(txn, relatives, payloads, "test")
    assert not txn.exists() and not (repo / relatives[1]).exists()


def test_recovery_rejects_nonprefix_installed_output_set():
    relatives = ("first", "second", "third")
    runtime._require_ordered_output_prefix(
        relatives, {"first": True, "second": True, "third": False})
    for states in (
        {"first": False, "second": True, "third": False},
        {"first": True, "second": False, "third": True},
    ):
        with pytest.raises(ValueError, match="ordered prefix"):
            runtime._require_ordered_output_prefix(relatives, states)


def test_public_m4_gate_recovers_validated_crash_left_tree_before_rebuild(
        tmp_path, monkeypatch):
    primary = tmp_path / "primary"; primary.mkdir(mode=0o700)
    (primary / "partial").write_text("partial\n")
    rebuild = tmp_path / "rebuild"
    transaction = tmp_path / "transaction"; transaction.mkdir(mode=0o700)
    monkeypatch.setattr(runtime, "M4_PRIMARY", primary)
    monkeypatch.setattr(runtime, "M4_REBUILD", rebuild)
    monkeypatch.setattr(runtime, "M4_TRANSACTION", transaction)
    monkeypatch.setattr(runtime, "M4_NEW", tuple())
    monkeypatch.setattr(runtime, "quarantine_guard", contextlib.nullcontext)
    calls = []
    def review(digest, *, allow_m4_recovery=False):
        calls.append(("review", allow_m4_recovery))
        return {"review": {"sha256": digest}}
    def build(digest, *, allow_m4_recovery=False):
        calls.append(("build", allow_m4_recovery))
        # The implementation owns descriptor validation and safe recursive
        # cleanup; the public gate must not blindly remove untrusted trees.
        assert primary.exists() and not rebuild.exists()
        assert transaction.exists()
        return {"stage_ready": True}
    monkeypatch.setattr(runtime, "verify_post_m3_review", review)
    monkeypatch.setattr(runtime, "_build_m4_impl", build)
    result = runtime.build_m4("a" * 64)
    assert result["stage_ready"] is True
    assert calls == [("review", True), ("build", True)]


def test_transaction_rejects_undeclared_staging_entry(tmp_path, monkeypatch):
    repo = tmp_path / "repo"; repo.mkdir()
    txn = tmp_path / "txn"; txn.mkdir(mode=0o700)
    (txn / "evil").write_text("x")
    monkeypatch.setattr(runtime, "ROOT", repo)
    with pytest.raises(ValueError, match="undeclared M4 transaction"):
        runtime._install_transaction(txn, ("x",), {"x": b"x"}, "test")
    assert not (repo / "x").exists()


def test_transaction_descriptor_rejects_symlink_identity(tmp_path, monkeypatch):
    repo = tmp_path / "repo"; repo.mkdir()
    txn = tmp_path / "txn"; txn.mkdir(mode=0o700)
    relative, raw = "x", b"x"
    entry = {"relative": relative, "staged": "00.payload", "size": 1,
             "sha256": runtime.base.sha_bytes(raw), "mode": 0o644}
    descriptor = runtime.base.canonical_bytes({"schema_version": "test",
                                                "protocol_id": runtime.PROTOCOL,
                                                "entries": [entry],
                                                "entries_sha256": runtime.base.sha_bytes(
                                                    runtime.base.canonical_bytes([entry]))})
    (txn / "00.payload").write_bytes(raw); (txn / "00.payload").chmod(0o600)
    backing = tmp_path / "descriptor"; backing.write_bytes(descriptor); backing.chmod(0o600)
    (txn / "transaction.json").symlink_to(backing)
    monkeypatch.setattr(runtime, "ROOT", repo)
    with pytest.raises(OSError):
        runtime._install_transaction(txn, (relative,), {relative: raw}, "test")


def test_complete_m4_comparison_covers_nonoutput_inputs(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    for root in (left, right):
        (root / "ordinary.txt").parent.mkdir(parents=True, exist_ok=True)
        (root / "ordinary.txt").write_text("same\n")
        for relative in runtime.M4_NEW:
            path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((relative + "\n").encode())
            path.chmod(0o644)
    payloads = runtime._compare_complete_m4_trees(left, right, {"ready": True}, {"ready": True})
    assert set(payloads) == set(runtime.M4_NEW)
    (right / "ordinary.txt").write_text("different\n")
    with pytest.raises(ValueError, match="complete M4 trees differ"):
        runtime._compare_complete_m4_trees(left, right, {"ready": True}, {"ready": True})


def test_two_root_m4_materialization_wires_real_extension_and_manifest_without_live_fallback(
        tmp_path, monkeypatch):
    left, right, projection_root = (tmp_path / name for name in ("left", "right", "projection"))
    fixed = {
        runtime.PLAN_PATH.relative_to(runtime.ROOT),
        runtime.PLAN_REVIEW.relative_to(runtime.ROOT),
        runtime.IMPLEMENTATION_REVIEW.relative_to(runtime.ROOT),
        runtime.POST_M3_REVIEW.relative_to(runtime.ROOT),
        runtime.continuation.CONTROLLER_PATH.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTROLLER_PATH.relative_to(runtime.ROOT),
        runtime.RUNTIME.relative_to(runtime.ROOT), runtime.RUNNER.relative_to(runtime.ROOT),
        runtime.LAUNCHER.relative_to(runtime.ROOT), runtime.RUNTIME_RFC.relative_to(runtime.ROOT),
        runtime.RUNTIME_TEST.relative_to(runtime.ROOT),
        runtime.GEN2_FAILURE_PATH.relative_to(runtime.ROOT),
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "protocol.json",
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "authorization_commitment.json",
        runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "ed25519_public.pem",
        runtime.CPU_NO_MODEL_TRACE.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTINUATION_RFC.relative_to(runtime.ROOT),
        runtime.immutable_continuation.CONTINUATION_TEST.relative_to(runtime.ROOT),
        runtime.immutable_continuation.M1_COMPLETION_PATH.relative_to(runtime.ROOT),
        Path("data/msae_independent_measurement_v3/protected_v1_manifest.json"),
        Path("data/msae_independent_measurement_v3/protected_v2_manifest.json"),
        Path("data/msae_independent_measurement_v3/data_baseline_manifest.json"),
    }
    candidate_relatives = sorted(
        {item.as_posix() for item in fixed} | set(runtime.M4_NEW[:-1]))

    def seed(root, **_kwargs):
        root.mkdir(mode=0o700)
        for relative in fixed:
            target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
            if target.name in {"protected_v1_manifest.json", "protected_v2_manifest.json",
                               "data_baseline_manifest.json"}:
                raw = b'{"entries":[]}\n'
            elif target.name == "authorization_commitment.json":
                raw = runtime.base.canonical_bytes({
                    "private_key_binding": {}, "nonce_directory": {}})
            else:
                raw = (relative.as_posix() + "\n").encode()
            target.write_bytes(raw); target.chmod(0o644)
        for relative in runtime.M4_NEW:
            (root / relative).parent.mkdir(parents=True, exist_ok=True)

    seed(projection_root)
    for relative in runtime.M4_NEW[:-1]:
        target = projection_root / relative
        target.write_text("placeholder\n"); target.chmod(0o644)
    directories = runtime._directory_entries(projection_root, candidate_relatives)

    monkeypatch.setattr(runtime, "_copy_complete_candidate_tree", seed)
    allowed_roots = {left, right}
    def checkpoints(*, root=runtime.ROOT):
        if root not in allowed_roots:
            raise AssertionError(f"live checkpoint fallback: {root}")
        return []
    monkeypatch.setattr(runtime, "checkpoint_registry", checkpoints)
    monkeypatch.setattr(runtime, "_candidate_relatives",
                        lambda **kwargs: candidate_relatives)
    monkeypatch.setattr(runtime, "endpoint_registry",
                        lambda: {"schema_version": "registry", "entries": []})
    monkeypatch.setattr(runtime, "environment_payload",
                        lambda closure, *, root=runtime.ROOT: {
                            "schema_version": "environment",
                            "closure_sha256": runtime.base.sha_bytes(
                                runtime.base.canonical_bytes(closure))})
    monkeypatch.setattr(runtime, "stage_a_payload",
                        lambda *, overlay_root=None: {
                            "schema_version": "stage", "stage_ready": True})
    monkeypatch.setattr(runtime, "closure_payload",
                        lambda checkpoints, *, root=runtime.ROOT:
                        runtime._extend_rooted_closure(
                            {"schema_version": "closure", "entries": []}, root=root))
    original_regular = runtime._regular_entry
    def no_live_regular(path, *, root=runtime.ROOT):
        if Path(path).is_relative_to(runtime.ROOT):
            raise AssertionError(f"live repository fallback: {path}")
        return original_regular(Path(path), root=root)
    monkeypatch.setattr(runtime, "_regular_entry", no_live_regular)
    descriptor = {"schema_version": "test"}
    left_stage = runtime._materialize_complete_m4(
        left, [], [], directories, build_descriptor=descriptor)
    right_stage = runtime._materialize_complete_m4(
        right, [], [], directories, build_descriptor=descriptor)
    payloads = runtime._compare_complete_m4_trees(
        left, right, left_stage, right_stage)
    assert set(payloads) == set(runtime.M4_NEW)


def test_candidate_manifest_construction_uses_only_explicit_tree_root(tmp_path, monkeypatch):
    tree = tmp_path / "tree"
    (tree / "data/msae_independent_measurement_v3").mkdir(parents=True)
    for name in ("protected_v1_manifest.json", "protected_v2_manifest.json",
                 "data_baseline_manifest.json"):
        (tree / "data/msae_independent_measurement_v3" / name).write_text('{"entries":[]}\n')
    for relative in (runtime.M4_NEW[0], runtime.M4_NEW[3]):
        path = tree / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n")
    commitment = tree / runtime.ACTIVE_CONFIG.relative_to(runtime.ROOT) / "authorization_commitment.json"
    commitment.parent.mkdir(parents=True, exist_ok=True)
    commitment.write_text('{"private_key_binding":{},"nonce_directory":{}}\n')
    observed_roots = []
    def checkpoints(*, root=runtime.ROOT):
        observed_roots.append(root)
        if root == runtime.ROOT:
            raise AssertionError("live checkpoint fallback")
        return []
    monkeypatch.setattr(runtime, "checkpoint_registry", checkpoints)
    monkeypatch.setattr(runtime, "_candidate_relatives",
                        lambda *, include_m4, root=runtime.ROOT, checkpoints=None: [])
    value = runtime.candidate_manifest_payload(tree, [], [])
    assert value["candidate_files"] == []
    assert observed_roots == [tree]


def test_anticipated_status_matches_git_semantics_for_ignored_m4_data(monkeypatch):
    ignored_data = runtime.M4_NEW[:3]
    for relative in ignored_data:
        result = subprocess.run(
            ["/usr/bin/git", "check-ignore", "--quiet", relative],
            cwd=runtime.ROOT, check=False)
        assert result.returncode == 0, relative
    monkeypatch.setattr(runtime, "_git_status", lambda: ["? existing.txt"])
    projected = runtime._anticipated_status()
    assert "? existing.txt" in projected
    assert all(f"? {relative}" not in projected for relative in ignored_data)
    assert all(f"? {relative}" in projected for relative in runtime.M4_NEW[3:-1])
    assert f"? {runtime.M4_NEW[-1]}" not in projected


def test_anticipated_status_normalizes_crash_left_transaction_and_m4_prefix(monkeypatch):
    transaction = runtime.M4_TRANSACTION.relative_to(runtime.ROOT).as_posix()
    monkeypatch.setattr(runtime, "_git_status", lambda: [
        "? ordinary.txt", f"? {transaction}/transaction.json",
        *(f"? {relative}" for relative in runtime.M4_NEW),
    ])
    projected = runtime._anticipated_status()
    assert "? ordinary.txt" in projected
    assert all(not line.startswith(f"? {transaction}") for line in projected)
    assert all(f"? {relative}" not in projected for relative in runtime.M4_NEW[:3])
    assert all(f"? {relative}" in projected for relative in runtime.M4_NEW[3:-1])
    assert f"? {runtime.M4_NEW[-1]}" not in projected


def test_recovery_manifest_directory_projection_removes_only_transaction_nlink(
        tmp_path, monkeypatch):
    repo = tmp_path / "repo"; provenance = repo / "provenance"
    provenance.mkdir(parents=True)
    transaction = provenance / ".transaction"; transaction.mkdir(mode=0o700)
    monkeypatch.setattr(runtime, "ROOT", repo)
    monkeypatch.setattr(runtime, "M4_TRANSACTION", transaction)
    current = [{"path": "provenance", "type": "directory", "mode": 0o755,
                "uid": os.getuid(), "nlink": provenance.stat().st_nlink}]
    projected = runtime._historical_manifest_directory_projection(current, recovery=True)
    assert projected[0]["nlink"] == current[0]["nlink"] - 1
    assert current[0]["nlink"] == provenance.stat().st_nlink


def test_m4_live_reauthorization_rejects_drift(tmp_path, monkeypatch):
    repo = tmp_path / "repo"; repo.mkdir()
    item = repo / "x"; item.write_text("one\n"); item.chmod(0o644)
    monkeypatch.setattr(runtime, "ROOT", repo)
    monkeypatch.setattr(runtime, "_git_status", lambda: ["? x"])
    monkeypatch.setattr(runtime, "_candidate_relatives", lambda **kwargs: ["x"])
    monkeypatch.setattr(runtime.base, "verify_baseline_projection", lambda phase: {})
    monkeypatch.setattr(runtime.base, "verify_protected_v1", lambda: 372)
    monkeypatch.setattr(runtime.base, "verify_protected_v2", lambda: 14)
    monkeypatch.setattr(runtime.base, "validate_source_exposure", lambda: {})
    snapshot = runtime._tree_entries(repo, ["x"])
    runtime._verify_live_m4_inputs(snapshot, ["? x"], [])
    item.write_text("two\n")
    with pytest.raises(ValueError, match="inputs drifted"):
        runtime._verify_live_m4_inputs(snapshot, ["? x"], [])


@pytest.mark.parametrize("defect", ["symlink", "mode", "hardlink"])
def test_transaction_rejects_existing_target_identity_defects(tmp_path, monkeypatch, defect):
    repo = tmp_path / "repo"; repo.mkdir()
    target = repo / "x"
    raw = b"x"
    if defect == "symlink":
        backing = tmp_path / "backing"; backing.write_bytes(raw)
        target.symlink_to(backing)
    else:
        target.write_bytes(raw)
        target.chmod(0o600 if defect == "mode" else 0o644)
        if defect == "hardlink":
            os.link(target, tmp_path / "second")
    monkeypatch.setattr(runtime, "ROOT", repo)
    with pytest.raises((ValueError, OSError)):
        runtime._install_transaction(tmp_path / "absent", ("x",), {"x": raw}, "test")


def test_terminal_success_and_failure_are_mutually_exclusive(tmp_path):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    runtime.commit_terminal_success(run, terminal_files())
    assert (run / "terminal_success/stage_b.json").is_file()
    assert runtime.commit_terminal_failure(run, {"status": "not_run"}) is False
    assert not (run / "terminal_failure").exists()


def test_terminal_failure_prevents_stage_b_exposure(tmp_path):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    assert runtime.commit_terminal_failure(run, {"status": "not_run"}) is True
    with pytest.raises(FileExistsError):
        runtime.commit_terminal_success(run, terminal_files())
    assert not (run / "terminal_success/stage_b.json").exists()


def test_interrupted_success_is_recoverable_as_failure(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    original = runtime.base.write_once
    calls = 0

    def fail_second(path, payload, mode=0o644):
        nonlocal calls
        if ".terminal_success_staging" in str(path):
            calls += 1
            if calls == 2:
                raise OSError("injected success write failure")
        return original(path, payload, mode)

    monkeypatch.setattr(runtime.base, "write_once", fail_second)
    with pytest.raises(OSError, match="injected"):
        runtime.commit_terminal_success(run, terminal_files())
    monkeypatch.setattr(runtime.base, "write_once", original)
    assert runtime.commit_terminal_failure(run, {"status": "not_run"}) is True
    assert (run / "terminal_failure/status.json").is_file()
    assert not (run / "terminal_success").exists()


def test_gpu_lock_validator_checks_content_and_identity(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    name = runtime.base.sha_bytes(uuid.encode("ascii")) + ".lock"
    lock = locks / name
    lock.write_bytes(runtime.base.canonical_bytes({"schema_version": "msae_gpu_uuid_lock_v1",
                                                   "gpu_uuid": uuid}))
    lock.chmod(0o600)
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
    try:
        assert runtime._validate_gpu_lock_fd(fd, uuid)["inode"] == os.fstat(fd).st_ino
        os.ftruncate(fd, 0); os.write(fd, b"bad"); os.fsync(fd)
        with pytest.raises(ValueError, match="content drift"):
            runtime._validate_gpu_lock_fd(fd, uuid)
    finally:
        os.close(fd)


def test_gpu_lock_acquisition_contends_and_path_substitution_blocks(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd, directory_fd, path = runtime._open_gpu_lock(uuid)
    try:
        with pytest.raises(BlockingIOError):
            runtime._open_gpu_lock(uuid)
        displaced = tmp_path / "displaced.lock"
        path.rename(displaced)
        path.write_bytes(runtime.base.canonical_bytes(
            {"schema_version": "msae_gpu_uuid_lock_v1", "gpu_uuid": uuid}))
        path.chmod(0o600)
        with pytest.raises(ValueError, match="FD/path"):
            runtime._validate_gpu_lock_fd(fd, uuid)
    finally:
        os.close(fd); os.close(directory_fd)


def test_gpu_lock_short_writes_are_completed_and_zero_write_stays_retryable(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(
        runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    original_write = os.write

    def short_write(fd, payload):
        return original_write(fd, payload[:max(1, len(payload) // 3)])

    monkeypatch.setattr(runtime.os, "write", short_write)
    fd, directory_fd, path = runtime._open_gpu_lock(uuid)
    try:
        expected = runtime.base.canonical_bytes(
            {"schema_version": "msae_gpu_uuid_lock_v1", "gpu_uuid": uuid})
        assert path.read_bytes() == expected
    finally:
        os.close(fd); os.close(directory_fd)

    path.unlink()
    monkeypatch.setattr(runtime.os, "write", lambda _fd, _payload: 0)
    with pytest.raises(OSError, match="zero-length write"):
        runtime._open_gpu_lock(uuid)
    assert path.read_bytes() == b""
    monkeypatch.setattr(runtime.os, "write", original_write)
    fd, directory_fd, _ = runtime._open_gpu_lock(uuid)
    os.close(fd); os.close(directory_fd)


def test_gpu_flock_contention_is_real_cross_process(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd, directory_fd, path = runtime._open_gpu_lock(uuid)
    code = ("import fcntl,os,sys; fd=os.open(sys.argv[1],os.O_RDWR); "
            "\ntry: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); print('acquired')"
            "\nexcept BlockingIOError: print('blocked')")
    try:
        child = subprocess.run([sys.executable, "-c", code, str(path)], check=True,
                               text=True, capture_output=True)
        assert child.stdout.strip() == "blocked"
    finally:
        os.close(fd); os.close(directory_fd)


def test_internal_broker_requires_live_launcher_capability_before_socket_or_gpu(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    monkeypatch.setattr(runtime, "LAUNCH_INTENT", run / "launcher_intent.json")
    touched = []
    monkeypatch.setattr(runtime.socket, "socket", lambda *args, **kwargs: touched.append(args))
    with pytest.raises(FileNotFoundError):
        runtime.broker(str(run / "broker.sock"), "GPU-1234567890abcdef", 0,
                       "a" * 64, "b" * 64)
    assert touched == [] and not (run / "logs").exists()


def test_launcher_intent_binds_capability_socket_gpu_and_lease(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    stage = prov / "stage_a.json"; stage.write_text("{}\n"); stage.chmod(0o644)
    authorization = run / "authorization.json"; authorization.write_text("{}\n")
    authorization.chmod(0o600)
    uuid = "GPU-1234567890abcdef"
    lock = locks / (runtime.base.sha_bytes(uuid.encode("ascii")) + ".lock")
    lock.write_bytes(runtime.base.canonical_bytes(
        {"schema_version": "msae_gpu_uuid_lock_v1", "gpu_uuid": uuid}))
    lock.chmod(0o600)
    capability = "a" * 64
    pid = os.getpid(); ticks = runtime.base._start_ticks(pid)
    intent = {"schema_version": "msae_v3_launcher_intent_v1",
              "protocol_id": runtime.PROTOCOL, "socket_path": str(run / "broker.sock"),
              "gpu_uuid": uuid, "gpu_index": 0, "lock_path": str(lock),
              "lock_device": lock.stat().st_dev, "lock_inode": lock.stat().st_ino,
              "stage_a_sha256": runtime.base.sha_file(stage),
              "authorization_envelope_sha256": runtime.base.sha_file(authorization),
              "launch_capability_sha256": runtime.base.sha_bytes(capability.encode("ascii")),
              "launcher_pid": pid, "launcher_start_ticks": ticks}
    intent_path = run / "launcher_intent.json"
    intent_path.write_bytes(runtime.base.canonical_bytes(intent)); intent_path.chmod(0o600)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    monkeypatch.setattr(runtime, "LAUNCH_INTENT", intent_path)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
    try:
        digest = runtime.base.sha_file(intent_path)
        assert runtime._validate_launcher_intent(
            str(run / "broker.sock"), uuid, 0, capability, digest, fd) == intent
        with pytest.raises(ValueError, match="exact socket/GPU/lock"):
            runtime._validate_launcher_intent(
                str(run / "other.sock"), uuid, 0, capability, digest, fd)
        with pytest.raises(ValueError, match="canonical bytes/digest"):
            runtime._validate_launcher_intent(
                str(run / "broker.sock"), uuid, 0, capability, "b" * 64, fd)
    finally:
        os.close(fd)


def test_launch_releases_gpu_lease_when_post_acquisition_setup_fails(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    uuid = "GPU-1234567890abcdef"
    commitment = {"gpu_lock_directory": runtime.base._directory_binding(locks)}
    (config / "authorization_commitment.json").write_bytes(
        runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime.base, "GPU_LOCK_DIR", locks)
    fd, directory_fd, path = runtime._open_gpu_lock(uuid)
    monkeypatch.setattr(runtime, "verify_candidate_manifest", lambda _phase: {})
    monkeypatch.setattr(runtime, "validate_stage_a", lambda: {})
    monkeypatch.setattr(runtime, "verify_authorization", lambda *args, **kwargs:
                        {"envelope_sha256": "a" * 64})
    monkeypatch.setattr(runtime, "_gpu_rows", lambda: [(0, 0, uuid, 0)])
    monkeypatch.setattr(runtime, "_open_gpu_lock", lambda _uuid: (fd, directory_fd, path))
    monkeypatch.setattr(runtime, "_launch_with_acquired_gpu",
                        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected setup")))
    with pytest.raises(OSError, match="injected setup"):
        runtime._launch_impl()
    code = ("import fcntl,os,sys; f=os.open(sys.argv[1],os.O_RDWR); "
            "fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); print('acquired')")
    child = subprocess.run([sys.executable, "-c", code, str(path)], check=True,
                           text=True, capture_output=True)
    assert child.stdout.strip() == "acquired"


def test_worker_environment_is_closed_and_inherited_escape_cannot_survive(monkeypatch):
    monkeypatch.setenv("LD_PRELOAD", "/tmp/escape.so")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/escape")
    value = runtime.worker_environment("GPU-1234567890abcdef", 3, 4, 5, 6)
    assert "LD_PRELOAD" not in value and "LD_LIBRARY_PATH" not in value
    assert value["CUBLAS_WORKSPACE_CONFIG"] == ":4096:8"
    assert value["MSAE_LEASE_FD"] == "3" and set(value) == (
        set(runtime.FROZEN_BASE_PROCESS_ENVIRONMENT) |
        set(runtime.FROZEN_WORKER_ENVIRONMENT) |
        {"CUDA_VISIBLE_DEVICES", "MSAE_LEASE_FD", "MSAE_GPU_UUID",
         "MSAE_READINESS_FD", "MSAE_FINAL_ACK_FD", "MSAE_CONFIRMED_FD"})


def test_authorization_nonce_consumption_is_exactly_once(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    data = tmp_path / "data"; data.mkdir(mode=0o700)
    nonce = tmp_path / "nonces"; nonce.mkdir(mode=0o700)
    locks = tmp_path / "locks"; locks.mkdir(mode=0o700)
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    review = tmp_path / "review.md"; review.write_text("VERDICT: SHIP\n"); review.chmod(0o644)
    for path in (prov / "prescore_candidate_manifest.json", prov / "stage_a.json",
                 data / "dependency_closure.json", config / "protocol.json"):
        path.write_text("{}\n")
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.PEM,
                                               serialization.PublicFormat.SubjectPublicKeyInfo)
    (config / "ed25519_public.pem").write_bytes(public)
    (config / "ed25519_public.pem").chmod(0o644)
    commitment = {"envelope_schema": "test_auth_v1", "public_key_sha256": runtime.base.sha_bytes(public),
                  "maximum_lifetime_seconds": 86400,
                  "nonce_directory": runtime.base._directory_binding(nonce)}
    (config / "authorization_commitment.json").write_bytes(runtime.base.canonical_bytes(commitment))
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", data)
    monkeypatch.setattr(runtime, "ACTIVE_NONCE_DIR", nonce)
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", review)
    monkeypatch.setattr(runtime, "_verify_existing_authorization_state", lambda: commitment)
    issued = int(time.time())
    unsigned = {"schema_version": "test_auth_v1", "protocol_id": runtime.PROTOCOL,
                "scope": "calibration_replay_only",
                "commitment_sha256": runtime.base.sha_file(config / "authorization_commitment.json"),
                "stage_a_sha256": runtime.base.sha_file(prov / "stage_a.json"),
                "protocol_config_sha256": runtime.base.sha_file(config / "protocol.json"),
                "dependency_closure_sha256": runtime.base.sha_file(data / "dependency_closure.json"),
                "prescore_candidate_manifest_sha256": runtime.base.sha_file(prov / "prescore_candidate_manifest.json"),
                "operator_instruction": runtime.OPERATOR_INSTRUCTION,
                "operator_instruction_sha256": runtime.base.sha_bytes(runtime.OPERATOR_INSTRUCTION.encode()),
                "review_sha256": runtime.base.sha_file(review), "review_verdict": "SHIP",
                "nonce": "a" * 64, "issued_unix": issued, "expires_unix": issued + 600}
    signature = private.sign(runtime.base.canonical_bytes(unsigned))
    envelope = {**unsigned, "signature_b64": base64.b64encode(signature).decode("ascii")}
    envelope_path = run / "authorization.json"
    envelope_path.write_bytes(runtime.base.canonical_bytes(envelope))
    envelope_path.chmod(0o600)
    runtime.verify_authorization(envelope_path, consume=False)
    original_write = os.write

    def short_write(fd, payload):
        return original_write(fd, payload[:max(1, len(payload) // 4)])

    monkeypatch.setattr(runtime.os, "write", short_write)
    result = runtime.verify_authorization(envelope_path, consume=True, run_root=run)
    monkeypatch.setattr(runtime.os, "write", original_write)
    assert result["envelope_sha256"] == runtime.base.sha_file(envelope_path)
    with pytest.raises(ValueError, match="already been consumed"):
        runtime.verify_authorization(envelope_path, consume=False)
    old_nonce = tmp_path / "old_nonces"
    nonce.rename(old_nonce)
    nonce.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="nonce-directory FD"):
        runtime.verify_authorization(envelope_path, consume=False)


def test_runner_readiness_requires_every_exact_lineage_field(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    data = tmp_path / "data"; data.mkdir(mode=0o700)
    nonce = tmp_path / "nonces"; nonce.mkdir(mode=0o700)
    stage = prov / "stage_a.json"; stage.write_text("{}\n"); stage.chmod(0o644)
    protocol = config / "protocol.json"; protocol.write_text("{}\n"); protocol.chmod(0o644)
    closure = data / "dependency_closure.json"; closure.write_text("{}\n"); closure.chmod(0o644)
    authorization = {"envelope_sha256": "e" * 64}
    record = nonce / f"{authorization['envelope_sha256']}.consumed"
    record_value = {"schema_version": "msae_v3_nonce_consumed_v2",
                    "authorization_file_sha256": authorization["envelope_sha256"],
                    "stage_a_sha256": runtime.base.sha_file(stage)}
    record.write_bytes(runtime.base.canonical_bytes(record_value)); record.chmod(0o600)
    record_st = record.lstat()
    attestation_value = {"schema_version": "msae_v3_nonce_attestation_v2",
                         "record_path": str(record), "record_device": record_st.st_dev,
                         "record_inode": record_st.st_ino, "record_mode": 0o600,
                         "record_sha256": runtime.base.sha_file(record),
                         "authorization_file_sha256": authorization["envelope_sha256"]}
    attestation = run / "nonce_consumed.json"
    attestation.write_bytes(runtime.base.canonical_bytes(attestation_value)); attestation.chmod(0o644)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", data)
    monkeypatch.setattr(runtime, "ACTIVE_NONCE_DIR", nonce)
    worker = {"worker_pid": 101, "worker_pgid": 101, "broker_pid": 99}
    expected = {"schema_version": "msae_v3_runner_ready_v1", "protocol_id": runtime.PROTOCOL,
                "worker_pid": 101, "worker_pgid": 101, "broker_pid": 99,
                "gpu_uuid": "GPU-1234567890abcdef",
                "stage_a_sha256": runtime.base.sha_file(stage),
                "protocol_config_sha256": runtime.base.sha_file(protocol),
                "dependency_closure_sha256": runtime.base.sha_file(closure),
                "authorization_envelope_sha256": authorization["envelope_sha256"],
                "nonce_attestation_sha256": runtime.base.sha_file(attestation),
                "pre_model": True}
    assert runtime.validate_runner_readiness(
        expected, worker, "GPU-1234567890abcdef", authorization) == attestation_value
    for key in expected:
        mutated = dict(expected); mutated[key] = None
        with pytest.raises(ValueError, match="exact lineage"):
            runtime.validate_runner_readiness(
                mutated, worker, "GPU-1234567890abcdef", authorization)
    moved = nonce / "../nonces/../wrong.consumed"
    bad_attestation = dict(attestation_value); bad_attestation["record_path"] = str(moved)
    attestation.write_bytes(runtime.base.canonical_bytes(bad_attestation))
    with pytest.raises(ValueError, match="exact derived consumed record"):
        runtime.validate_runner_readiness(
            {**expected, "nonce_attestation_sha256": runtime.base.sha_file(attestation)},
            worker, "GPU-1234567890abcdef", authorization)
    attestation.write_bytes(runtime.base.canonical_bytes(attestation_value))
    record.write_bytes(runtime.base.canonical_bytes({**record_value, "stage_a_sha256": "0" * 64}))
    with pytest.raises(ValueError, match="identity mismatch"):
        runtime.validate_runner_readiness(
            {**expected, "nonce_attestation_sha256": runtime.base.sha_file(attestation)},
            worker, "GPU-1234567890abcdef", authorization)


def test_terminate_group_escalates_without_targeting_invalid_groups(monkeypatch):
    calls = []
    monkeypatch.setattr(runtime.os, "killpg", lambda pgid, sig: calls.append((pgid, sig)))
    runtime._terminate_group(-1)
    assert calls == []


def test_terminate_group_kills_a_term_resistant_real_process_group():
    process = subprocess.Popen(
        [sys.executable, "-c",
         "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
         "print('R', flush=True); time.sleep(60)"],
        start_new_session=True, stdout=subprocess.PIPE, text=True)
    try:
        assert process.stdout is not None and process.stdout.readline().strip() == "R"
        runtime._terminate_group(process.pid, grace=0.05)
        assert process.wait(timeout=3) == -9
    finally:
        if process.poll() is None:
            os.killpg(process.pid, 9)


def test_parent_death_watchdog_kills_worker_when_broker_exits(tmp_path):
    runtime_path = ROOT / "scripts/msae_independent_measurement_v3_post_m2_gen4_runtime.py"
    controller_path = ROOT / "scripts/msae_independent_measurement_v3_post_m2_gen4.py"
    script = f'''\
import importlib.util, os, sys, time, types
controller_path={str(controller_path)!r}
controller=types.ModuleType("msae_independent_measurement_v3_post_m2_gen4")
controller.__file__=controller_path; controller.__package__=None
sys.modules[controller.__name__]=controller
with open(controller_path,"rb") as handle: controller_raw=handle.read()
exec(compile(controller_raw,controller_path,"exec"),controller.__dict__)
spec=controller.source_only_module_spec("watchdog_runtime", {str(runtime_path)!r})
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
out_fd={{{{OUT_FD}}}}
ready_r, ready_w = os.pipe()
pid=os.fork()
if pid == 0:
    os.close(ready_r)
    module.install_parent_death_watchdog(os.getppid())
    os.write(out_fd, (str(os.getpid())+"\\n").encode())
    os.write(ready_w, b"R")
    while True: time.sleep(1)
os.close(ready_w)
os.read(ready_r, 1)
os._exit(0)
'''
    read_fd, write_fd = os.pipe()
    script = script.replace("{{OUT_FD}}", str(write_fd))
    parent = subprocess.Popen([sys.executable, "-c", script], pass_fds=(write_fd,))
    os.close(write_fd)
    try:
        worker_pid = int(os.read(read_fd, 64).strip())
        assert parent.wait(timeout=5) == 0
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and (Path("/proc") / str(worker_pid)).exists():
            try:
                status = (Path("/proc") / str(worker_pid) / "stat").read_text().split()[2]
            except (FileNotFoundError, ProcessLookupError):
                break
            if status == "Z":
                break
            time.sleep(0.05)
        try:
            final_status = (Path("/proc") / str(worker_pid) / "stat").read_text().split()[2]
        except (FileNotFoundError, ProcessLookupError):
            final_status = "gone"
        assert final_status in {"gone", "Z"}
    finally:
        os.close(read_fd)


def test_supervisor_claims_terminal_failure_when_broker_is_killed(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    result = runtime._supervise_broker_process(
        [sys.executable, "-c", "import os,signal; os.kill(os.getpid(),signal.SIGKILL)"],
        runtime.FROZEN_BASE_PROCESS_ENVIRONMENT)
    assert result == -signal.SIGKILL
    status = runtime.base.read_json(run / "terminal_failure/status.json")
    failure = runtime.base.read_json(run / "terminal_failure/technical_failure.json")
    assert status["status"] == "technical_failure_not_run" and status["stage_b_ready"] is False
    assert failure["status"] == "not_run" and failure["stage_b_written"] is False
    assert not (run / "terminal_success").exists()


def test_supervisor_kills_descendant_group_after_worker_leader_exit(tmp_path, monkeypatch):
    run = tmp_path / "run"; run.mkdir(mode=0o700)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    record = run / "lock_acquired.json"
    child_pid_file = run / "child.pid"
    code = r'''
import ctypes, json, os, signal, sys, time
record, child_file = sys.argv[1:]
leader = os.fork()
if leader == 0:
    os.setpgid(0, 0)
    leader_pid = os.getpid()
    raw = open('/proc/self/stat').read()
    ticks = int(raw[raw.rfind(')')+2:].split()[19])
    grandchild = os.fork()
    if grandchild == 0:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        ctypes.CDLL(None).prctl(15, b'a b)', 0, 0, 0)
        with open(child_file, 'w') as f: f.write(str(os.getpid()))
        while True: time.sleep(1)
    value = {'worker_pid': leader_pid, 'worker_start_ticks': ticks, 'worker_pgid': leader_pid}
    with open(record, 'w') as f:
        f.write(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n')
    os.chmod(record, 0o644)
    while not os.path.exists(child_file): time.sleep(0.01)
    os._exit(0)
os.waitpid(leader, 0)
os._exit(0)
'''
    result = runtime._supervise_broker_process(
        [sys.executable, "-c", code, str(record), str(child_pid_file)],
        runtime.FROZEN_BASE_PROCESS_ENVIRONMENT)
    child_pid = int(child_pid_file.read_text())
    worker_pgid = runtime.base.read_json(record)["worker_pgid"]
    assert result == 0
    assert not runtime._group_live_pids(worker_pgid)
    assert (run / "terminal_failure/status.json").is_file()


def test_failed_handoff_extinction_kills_real_processes_and_socket(tmp_path):
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    ticks = runtime.base._start_ticks(process.pid)
    socket_path = tmp_path / "absent.sock"
    try:
        runtime._verify_failed_handoff_extinction(
            socket_path, "absent-session", [(process.pid, ticks)])
        process.wait(timeout=3)
        assert process.returncode in {-signal.SIGTERM, -signal.SIGKILL}
        assert not socket_path.exists()
    finally:
        if process.poll() is None:
            process.kill()


def test_candidate_set_is_unique_and_manifest_self_excluded():
    paths = runtime._candidate_relatives(include_m4=True)
    assert len(paths) == len(set(paths))
    assert runtime.M4_NEW[-1] not in paths
    assert set(runtime.M4_NEW[:-1]) <= set(paths)
    assert all("post_m2_gen4" in path for path in runtime.M4_NEW[3:])


def test_two_phase_model_gate_blocks_until_durable_ack():
    final_r, final_w = os.pipe(); confirmed_r, confirmed_w = os.pipe()
    marker_r, marker_w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(final_w); os.close(confirmed_r); os.close(marker_r)
        runtime.confirm_pre_model_gate(final_r, confirmed_w)
        os.write(marker_w, b"M")
        os._exit(0)
    os.close(final_r); os.close(confirmed_w); os.close(marker_w)
    try:
        os.set_blocking(marker_r, False)
        with pytest.raises(BlockingIOError):
            os.read(marker_r, 1)
        os.write(final_w, b"F"); os.close(final_w)
        assert os.read(confirmed_r, 1) == b"A"
        deadline = time.monotonic() + 2
        marker = b""
        while time.monotonic() < deadline and not marker:
            try:
                marker = os.read(marker_r, 1)
            except BlockingIOError:
                time.sleep(0.01)
        assert marker == b"M"
        os.waitpid(pid, 0)
    finally:
        for fd in (confirmed_r, marker_r):
            try: os.close(fd)
            except OSError: pass


def test_runner_uses_two_phase_model_gate_and_atomic_terminal_only():
    source = (ROOT / "scripts/run_msae_independent_calibration_v3_gen4.py").read_text()
    assert "--final-ack-fd" in source and "--confirmed-fd" in source
    assert "runtime.confirm_pre_model_gate(args.final_ack_fd, args.confirmed_fd)" in source
    assert "commit_terminal_success" in source
    assert 'run_root / "stage_b.json"' not in source
    assert "protocol._fsync_directory(cache_root)" in source
    assert "protocol._fsync_directory(pooling_path.parent)" in source


def test_runner_rejects_alternate_failure_root_without_writing(tmp_path):
    alternate = tmp_path / "alternate"; alternate.mkdir(mode=0o700)
    result = subprocess.run([
        str(ROOT / ".venv-atlas/bin/python"), "-S", "-B", "-I",
        str(ROOT / "scripts/run_msae_independent_calibration_v3_gen4.py"),
        "--run-root", str(alternate), "--gpu-uuid", "GPU-fake",
        "--broker-pid", "1", "--readiness-fd", "0", "--final-ack-fd", "0",
        "--confirmed-fd", "0"], text=True, capture_output=True)
    assert result.returncode != 0
    assert list(alternate.iterdir()) == []


def test_selected_tolerance_with_failed_unit_replay_is_scientific_ineligible():
    assert runtime._pooling_disposition(["0.000001", "0.000005"],
                                        [True, False, True, True]) == (
        "ineligible", ["unit_batch_selector_failure"])
    assert runtime._pooling_disposition(None, [False] * 4) == (
        "ineligible", ["no_registered_tolerance"])
    assert runtime._pooling_disposition(["0.000001", "0.000005"], [True] * 4) == (
        "eligible", [])


def test_nonisolated_controller_entry_is_rejected_before_any_command(tmp_path):
    result = subprocess.run(
        [str(ROOT / ".venv-atlas/bin/python"), "-B", "-I",
         str(runtime.continuation.CONTROLLER_PATH), "build-m2-completion"],
        text=True, capture_output=True)
    assert result.returncode != 0
    assert "require -S -I -B interpreter isolation" in result.stderr


def test_gen4_terminal_payload_preserves_two_failed_gen3_invocations_honestly():
    value = runtime._gen3_terminal_payload()
    assert value["status"] == "failed_before_first_protocol_state_write"
    assert value["setup_m3_command_attempts"] == 2
    assert value["setup_m3_attempt_statuses"] == ["failed_prewrite", "failed_prewrite"]
    disclosed = value["operator_disclosed"]["invocations"]
    assert disclosed[0]["full_transcript_available"] is False
    assert disclosed[1]["transcript_size"] == 935
    assert disclosed[1]["transcript_sha256"] == \
        "e39e1583d30ce5eb0aa5277ff88d3eb37bee2eb357d8e68ca366591847413020"
    assert value["mechanically_reproduced_source_control_flow"][
        "raise_dominates_first_protocol_write"] is True
    observed = value["mechanically_observed_current_absence"]
    assert observed["evidence_class"] == "current_state_not_historical_syscall_observation"
    assert observed["sealed_payload_content_reads"] == 0
    assert "protocol_writes_observed" not in value


def test_historical_preflight_verification_has_no_write_or_fsync_surface(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("read-only preflight attempted a write/fsync")
    monkeypatch.setattr(runtime.base, "write_once", forbidden)
    monkeypatch.setattr(runtime.base, "install_json", forbidden)
    monkeypatch.setattr(runtime.os, "fsync", forbidden)
    value = runtime._verify_historical_preflight_readonly()
    assert value["successor_generation"] == "post_m2_gen2"
    assert runtime.base.sha_file(runtime.PREFLIGHT_FAILURE_PATH) == \
        runtime.HISTORICAL_PREFLIGHT_SHA256


def test_exact_gen4_cli_shape_rejects_reordering_duplicates_and_old_routes():
    setup = [
        "setup-m3-gen4",
        "--reviewed-m2-sha256", runtime.M2_REVIEWED_COMPLETION_SHA256,
        "--failed-gen3-plan-review-sha256", runtime.FAILED_GEN3_PLAN_REVIEW_SHA256,
        "--failed-gen3-implementation-review-sha256",
        runtime.FAILED_GEN3_IMPLEMENTATION_REVIEW_SHA256,
        "--gen4-plan-review-sha256", runtime.FROZEN_PLAN_REVIEW_SHA256,
        "--gen4-implementation-review-sha256", "a" * 64,
    ]
    runtime._require_exact_command_shape(setup)
    for defective in (
        [*setup[:3], *setup[5:7], *setup[3:5], *setup[7:]],
        [*setup, "--gen4-implementation-review-sha256", "a" * 64],
        ["setup-m3", *setup[1:]],
        ["build-m4-gen4", "--post-m3-review-sha256", "A" * 64],
        ["sign-gen4", "extra"],
    ):
        with pytest.raises(ValueError):
            runtime._require_exact_command_shape(defective)


def test_atomic_publisher_recovers_only_exact_prefix_partial(tmp_path):
    target = tmp_path / "artifact.json"
    raw = b'{"schema":"registered"}\n'
    partial = tmp_path / ".artifact.json.partial"
    partial.write_bytes(raw[:7]); partial.chmod(0o644)
    runtime._atomic_publish(target, raw, 0o644)
    assert target.read_bytes() == raw and not partial.exists()
    bad = tmp_path / "bad.json"
    bad_partial = tmp_path / ".bad.json.partial"
    bad_partial.write_bytes(b"wrong"); bad_partial.chmod(0o644)
    with pytest.raises(ValueError, match="exact prefix"):
        runtime._atomic_publish(bad, raw, 0o644)
    assert not bad.exists() and bad_partial.exists()


def test_setup_prefix_validator_rejects_receipt_hole(tmp_path, monkeypatch):
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    journal = prov / ".setup_m3_gen4_transaction"; journal.mkdir(mode=0o700)
    transaction = journal / "transaction.json"
    transaction.write_bytes(runtime.base.canonical_bytes({"schema": "test"})); transaction.chmod(0o600)
    receipt2 = journal / runtime.SETUP_RECEIPT_NAMES[1]
    receipt2.write_bytes(runtime.base.canonical_bytes({"schema": "test"})); receipt2.chmod(0o600)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime, "SETUP_JOURNAL", journal)
    monkeypatch.setattr(runtime, "SETUP_MANIFEST", prov / "setup_m3_gen4_manifest.json")
    monkeypatch.setattr(runtime, "M4_NEW", tuple())
    monkeypatch.setattr(runtime, "M4_TRANSACTION", tmp_path / "m4txn")
    monkeypatch.setattr(runtime, "M4_PRIMARY", tmp_path / "primary")
    monkeypatch.setattr(runtime, "M4_REBUILD", tmp_path / "rebuild")
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", tmp_path / "post")
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", tmp_path / "prescore")
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", tmp_path / "run")
    monkeypatch.setattr(runtime, "_validate_gen3_review_namespace", lambda phase: None)
    monkeypatch.setattr(runtime, "_post_m3_forbidden_tmp_patterns", lambda: tuple())
    with pytest.raises(ValueError, match="receipt set is not a prefix"):
        runtime._validate_setup_namespace_preconditions({"status": "failed"})


def test_sign_transaction_reuses_bound_random_bytes_after_rename_failure(
        tmp_path, monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    config = tmp_path / "config"; config.mkdir(mode=0o700)
    prov = tmp_path / "prov"; prov.mkdir(mode=0o700)
    data = tmp_path / "data"; data.mkdir(mode=0o700)
    nonce = tmp_path / "state/nonces"; nonce.mkdir(mode=0o700, parents=True)
    run = tmp_path / "run"
    private_path = tmp_path / "keys/private.pem"; private_path.parent.mkdir(mode=0o700)
    private = Ed25519PrivateKey.generate()
    private_raw = private.private_bytes(serialization.Encoding.PEM,
                                        serialization.PrivateFormat.PKCS8,
                                        serialization.NoEncryption())
    private_path.write_bytes(private_raw); private_path.chmod(0o600)
    public_raw = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    for path, raw in (
        (config / "ed25519_public.pem", public_raw),
        (config / "authorization_commitment.json", b"commitment\n"),
        (config / "protocol.json", b"protocol\n"),
        (prov / "stage_a.json", b"stage\n"),
        (prov / "prescore_candidate_manifest.json", b"manifest\n"),
        (data / "dependency_closure.json", b"closure\n"),
    ):
        path.write_bytes(raw); path.chmod(0o644)
    implementation = tmp_path / "implementation.md"
    post_m3 = tmp_path / "post_m3.md"
    prescore = tmp_path / "prescore.md"
    for path, raw in ((implementation, b"implementation\n"),
                      (post_m3, b"post-m3\n"),
                      (prescore, b"prescore\n")):
        path.write_bytes(raw); path.chmod(0o644)
    st = private_path.lstat()
    binding = {"path": str(private_path), "device": st.st_dev, "inode": st.st_ino,
               "uid": st.st_uid, "mode": 0o600, "nlink": 1, "size": st.st_size,
               "mtime_ns": st.st_mtime_ns, "ctime_ns": st.st_ctime_ns,
               "public_key_match": True}
    commitment = {
        "envelope_schema": "msae_v3_signed_authorization_v2",
        "maximum_lifetime_seconds": 86400,
        "operator_instruction_sha256": runtime.base.sha_bytes(
            runtime.OPERATOR_INSTRUCTION.encode()),
        "private_key_binding": binding,
        "public_key_sha256": runtime.base.sha_bytes(public_raw),
        "nonce_directory": runtime.base._directory_binding(nonce),
    }
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PROV", prov)
    monkeypatch.setattr(runtime, "ACTIVE_M4_DATA", data)
    monkeypatch.setattr(runtime, "ACTIVE_NONCE_DIR", nonce)
    monkeypatch.setattr(runtime, "ACTIVE_PRIVATE_KEY", private_path)
    monkeypatch.setattr(runtime, "ACTIVE_RUN_ROOT", run)
    monkeypatch.setattr(runtime, "SIGN_TRANSACTION", run / ".sign_transaction")
    monkeypatch.setattr(runtime, "IMPLEMENTATION_REVIEW", implementation)
    monkeypatch.setattr(runtime, "POST_M3_REVIEW", post_m3)
    monkeypatch.setattr(runtime, "PRESCORE_REVIEW", prescore)
    phases = []
    monkeypatch.setattr(runtime, "verify_candidate_manifest",
                        lambda phase: phases.append(phase) or {"eligible": True})
    monkeypatch.setattr(runtime, "_verify_existing_authorization_state",
                        lambda **kwargs: commitment)
    original_rename = runtime._rename_noreplace
    calls = 0
    def fail_once(source, destination):
        nonlocal calls
        if destination.name == "authorization.json":
            calls += 1
        if destination.name == "authorization.json" and calls == 1:
            raise OSError("injected rename failure")
        return original_rename(source, destination)
    monkeypatch.setattr(runtime, "_rename_noreplace", fail_once)
    with pytest.raises(OSError, match="injected rename failure"):
        runtime._sign_authorization_impl()
    descriptor_before = (run / ".sign_transaction/transaction.json").read_bytes()
    staged_before = (run / ".sign_transaction/authorization.payload").read_bytes()
    output = runtime._sign_authorization_impl()
    assert runtime.base.canonical_bytes(output) == staged_before
    assert not (run / ".sign_transaction").exists()
    assert (run / "authorization.json").read_bytes() == staged_before
    assert runtime.base.sha_bytes(descriptor_before) != runtime.base.sha_bytes(staged_before)
    assert phases == ["post_review", "sign_recovery", "post_signature"]
