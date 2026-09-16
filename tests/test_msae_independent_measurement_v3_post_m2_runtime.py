from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import signal
import copy
import subprocess
import sys
import time
import base64

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "msae_v3_post_m2_runtime", ROOT / "scripts/msae_independent_measurement_v3_post_m1_runtime.py")
assert SPEC and SPEC.loader
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


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


def test_successor_config_projects_exactly_to_the_reviewed_generic_schema():
    from msae_measurement_remediation_v1 import validate_draft_config
    successor = runtime.base.read_json(runtime.V3_CONFIG / "protocol.json")
    generic = runtime.generic_config_projection(successor)
    assert set(generic) == set(runtime.GENERIC_CONFIG_KEYS)
    assert not set(runtime.SUCCESSOR_CONFIG_KEYS) & set(generic)
    raw = runtime.base.canonical_bytes(generic)
    assert validate_draft_config(raw, runtime.base.sha_bytes(raw))["status"] == "ready"
    with pytest.raises(ValueError, match="successor config key mismatch"):
        runtime.generic_config_projection({**successor, "unreviewed": True})


def test_generic_replay_bundle_changes_only_the_config_binding():
    bundle = {"schema_version": "msae_calibration_replay_bundle_v1",
              "protocol_config_sha256": "a" * 64, "replay_registry_sha256": "b" * 64,
              "source_role": "calibration", "source_revision": "c" * 64,
              "partition": "calibration-public", "observations": {}}
    projected = runtime.generic_replay_bundle(bundle, "d" * 64)
    assert projected == {**bundle, "protocol_config_sha256": "d" * 64}
    with pytest.raises(ValueError, match="replay-bundle key mismatch"):
        runtime.generic_replay_bundle({**bundle, "extra": 1}, "d" * 64)


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
        runtime.setup_m3("0" * 64)


def test_failed_m3_preflight_pins_match_the_preserved_bytes():
    assert runtime.base.sha_file(runtime.V3_CONFIG / "protocol.json") == runtime.FAILED_M3_CONFIG_SHA256
    assert runtime.base.sha_file(runtime.V3_CONFIG / "authorization_commitment.json") == \
        runtime.FAILED_M3_COMMITMENT_SHA256
    assert runtime.base.sha_file(runtime.V3_CONFIG / "ed25519_public.pem") == \
        runtime.FAILED_M3_PUBLIC_SHA256


def test_m3_existing_protocol_rejects_symlink_before_acceptance(tmp_path, monkeypatch):
    config = tmp_path / "config"; config.mkdir(mode=0o700)
    private = tmp_path / "private"; private.write_bytes(b"key")
    for name in ("ed25519_public.pem", "authorization_commitment.json"):
        (config / name).write_bytes(b"x")
    cpu_trace = config / "cpu_no_model_public_entry_trace.json"
    cpu_trace.write_bytes(runtime.base.canonical_bytes({})); cpu_trace.chmod(0o644)
    backing = tmp_path / "protocol.json"; backing.write_bytes(runtime.base.canonical_bytes({"x": 1}))
    (config / "protocol.json").symlink_to(backing)
    monkeypatch.setattr(runtime, "ACTIVE_CONFIG", config)
    monkeypatch.setattr(runtime, "ACTIVE_PRIVATE_KEY", private)
    monkeypatch.setattr(runtime, "CPU_NO_MODEL_TRACE", cpu_trace)
    monkeypatch.setattr(runtime, "verify_m2_completion", lambda digest: {})
    monkeypatch.setattr(runtime, "preserve_m3_preflight", lambda: {})
    monkeypatch.setattr(runtime, "checkpoint_registry", lambda: [])
    monkeypatch.setattr(runtime, "_protocol_config_payload", lambda *a, **k: {"x": 1})
    monkeypatch.setattr(runtime, "cpu_no_model_public_entry_trace", lambda: {})
    monkeypatch.setattr(runtime, "_validate_cpu_no_model_trace", lambda *a, **k: {})
    monkeypatch.setattr(runtime, "_verify_existing_authorization_state",
                        lambda: {"contains_execution_authorization": False})
    with pytest.raises(OSError):
        runtime.setup_m3(runtime.M2_REVIEWED_COMPLETION_SHA256)


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
    monkeypatch.setattr(runtime, "_prescore_evidence_paths", lambda digest: (check, trace))
    good = "\n".join(["VERDICT: SHIP", "PRESCORE_CANDIDATE_MANIFEST_SHA256: " + "c" * 64,
                       "STAGE_A_SHA256: " + "a" * 64,
                       "DEPENDENCY_CLOSURE_SHA256: " + "b" * 64,
                       "PRESCORE_CHECK_SHA256: " + runtime.base.sha_file(check),
                       "PRESCORE_TRACE_SHA256: " + runtime.base.sha_file(trace),
                       "SEALED_PAYLOAD_CONTENT_READS: 0"])
    runtime._strict_review_verdict(good, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict("VERDICT: BLOCK\n" + good, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(good + "\nSTAGE_A_SHA256: " + "a" * 64, manifest, "c" * 64)
    with pytest.raises(ValueError):
        runtime._strict_review_verdict(" VERDICT: BLOCK\n" + good, manifest, "c" * 64)


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
    monkeypatch.setattr(runtime, "V3_DATA", data)
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
    runner = tmp_path / "scripts/run_msae_independent_calibration_v3.py"
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
    runner = tmp_path / "scripts/run_msae_independent_calibration_v3.py"
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
    runner = tmp_path / "scripts/run_msae_independent_calibration_v3.py"
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


def test_static_value_flow_ledger_closes_caller_argv_and_helper_return_bypasses(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    module = tmp_path / "scripts/msae_independent_measurement_v3_post_m1_runtime.py"
    original = module.read_text()
    module.write_text(original.replace(
        'argv = [str(ROOT / ".venv-atlas/bin/python"), "-S", "-B", "-I",\n'
        '            str(continuation.CONTROLLER_PATH), "broker",',
        'argv = ["/bin/false", "-S", "-B", "-I",\n'
        '            str(continuation.CONTROLLER_PATH), "broker",', 1))
    with pytest.raises(ValueError, match="local value-flow AST ledger drift"):
        runtime._static_closure_analysis(root=tmp_path)


def test_static_ledger_self_exclusions_are_syntactically_inert(tmp_path):
    import shutil
    for relative in runtime.LOCAL_PYTHON_ENTRYPOINTS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    module = tmp_path / "scripts/msae_independent_measurement_v3_post_m1_runtime.py"
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
    value = runtime.cpu_no_model_public_entry_trace()
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
    monkeypatch.setattr(runtime, "ROOT", repo)
    original = runtime.base.write_once
    calls = 0

    def interrupted(path, payload, mode=0o644):
        nonlocal calls
        if path.is_relative_to(repo):
            if calls == 1:
                calls += 1
                raise OSError("injected")
            calls += 1
        return original(path, payload, mode)

    monkeypatch.setattr(runtime.base, "write_once", interrupted)
    with pytest.raises(OSError, match="injected"):
        runtime._install_transaction(root, relatives, payloads, "test")
    monkeypatch.setattr(runtime.base, "write_once", original)
    runtime._install_transaction(root, relatives, payloads, "test")
    assert not root.exists()
    assert all((repo / relative).read_bytes() == payloads[relative] for relative in relatives)


def test_transaction_rejects_undeclared_staging_entry(tmp_path, monkeypatch):
    repo = tmp_path / "repo"; repo.mkdir()
    txn = tmp_path / "txn"; txn.mkdir(mode=0o700)
    (txn / "evil").write_text("x")
    monkeypatch.setattr(runtime, "ROOT", repo)
    with pytest.raises(ValueError, match="undeclared transaction"):
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
    monkeypatch.setattr(runtime, "V3_DATA", data)
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
    monkeypatch.setattr(runtime, "V3_DATA", data)
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
    runtime_path = ROOT / "scripts/msae_independent_measurement_v3_post_m1_runtime.py"
    script = f'''\
import importlib.util, os, time
spec=importlib.util.spec_from_file_location("watchdog_runtime", {str(runtime_path)!r})
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
    assert all("post_m2_gen2" in path for path in runtime.M4_NEW[3:])


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
    source = (ROOT / "scripts/run_msae_independent_calibration_v3.py").read_text()
    assert "--final-ack-fd" in source and "--confirmed-fd" in source
    assert "runtime.confirm_pre_model_gate(args.final_ack_fd, args.confirmed_fd)" in source
    assert "commit_terminal_success" in source
    assert 'run_root / "stage_b.json"' not in source
    assert "protocol._fsync_directory(cache_root)" in source
    assert "protocol._fsync_directory(pooling_path.parent)" in source


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
