#!/usr/bin/env python3
"""CPU-only provenance rebind of the frozen atlas-completion baseline."""
from __future__ import annotations
import pickle
import sys
import time
from pathlib import Path

from msa_completion_common import (
    atomic_write_bytes, atomic_write_json, process_resource_accounting, read_json,
    runtime_environment, sha256_file, stage_publication_lock, terminal_state, utc_now,
    write_terminal,
)
from msa_completion_continuation_common import (
    BASELINE_HASHES, BASELINE_SOURCE, CONFIG, RUN_ROOT, SCIENTIFIC_BASELINE_FIELDS,
    publish_technical_stop, verify_continuation_freeze, verify_fixed_source_hashes,
    verify_baseline_science_payloads, verify_rebound_baseline,
    verify_source_inventory,
)


def main() -> None:
    started = time.monotonic()
    started_utc = utc_now()
    stage = RUN_ROOT / "baseline"
    try:
        freeze = verify_continuation_freeze()
        verify_source_inventory()
        verify_fixed_source_hashes()
        if terminal_state(stage) is not None or (stage.exists() and any(stage.iterdir())):
            raise RuntimeError(f"baseline provenance rebind is create-once: {stage}")
        source_result_path = BASELINE_SOURCE / "baseline.json"
        source_bundle_path = BASELINE_SOURCE / "baseline_bundle.pkl"
        source_result = read_json(source_result_path)
        with source_bundle_path.open("rb") as handle:
            source_bundle = pickle.load(handle)
        config = read_json(CONFIG)
        config_sha = sha256_file(CONFIG)
        attestation = {
            str(CONFIG.resolve()): {"sha256": config_sha, "size": CONFIG.stat().st_size},
            str(Path(freeze["_freeze_record_path"])): {
                "sha256": freeze["_freeze_record_sha256"],
                "size": Path(freeze["_freeze_record_path"]).stat().st_size,
            },
        }
        for name, digest in BASELINE_HASHES.items():
            path = BASELINE_SOURCE / name
            attestation[str(path.resolve())] = {"sha256": digest, "size": path.stat().st_size}
        rebound = dict(source_result)
        rebound.update({
            "config_sha256": config_sha,
            "completion_bundle_sha256": freeze["bundle_sha256"],
            "resolved_config": config,
            "resolved_arguments": {
                "mode": "cpu_provenance_rebind",
                "source_baseline": str(source_result_path.relative_to(source_result_path.parents[3])),
                "output": str(stage),
            },
            "device": "cpu",
            "environment": runtime_environment("cpu"),
            "input_attestation": attestation,
            "elapsed_sec": time.monotonic() - started,
            "started_utc": started_utc,
            "ended_utc": utc_now(),
            "provenance_rebind": {
                "schema_version": "atlas_completion_baseline_provenance_rebind_v1",
                "source_result_sha256": BASELINE_HASHES["baseline.json"],
                "source_bundle_sha256": BASELINE_HASHES["baseline_bundle.pkl"],
                "scientific_fields_exact": list(SCIENTIFIC_BASELINE_FIELDS),
                "scientific_equality": True,
                "diagnostic_continuation_only": True,
                "decision_promotion_allowed": False,
            },
        })
        rebound_bundle = dict(source_bundle)
        rebound_bundle["completion_bundle_sha256"] = freeze["bundle_sha256"]
        verify_baseline_science_payloads(
            source_result, rebound, source_bundle, rebound_bundle,
            continuation_bundle_sha256=freeze["bundle_sha256"])
        stage.mkdir(parents=True, exist_ok=False)
        result_path = stage / "baseline.json"
        bundle_path = stage / "baseline_bundle.pkl"
        with stage_publication_lock(stage):
            atomic_write_bytes(bundle_path, pickle.dumps(rebound_bundle, protocol=5))
            atomic_write_json(result_path, rebound)
            write_terminal(stage, complete=True, payload={
                "schema_version": "atlas_completion_baseline_provenance_rebind_complete_v1",
                "result_sha256": sha256_file(result_path),
                "bundle_sha256": sha256_file(bundle_path),
                "config_sha256": config_sha,
                "completion_bundle_sha256": freeze["bundle_sha256"],
                "resolved_config": config,
                "resolved_arguments": rebound["resolved_arguments"],
                "device": "cpu",
                "environment": rebound["environment"],
                "started_utc": started_utc,
                "resource_accounting": process_resource_accounting(
                    stage, elapsed_sec=time.monotonic() - started, device=None),
                "input_attestation": attestation,
                "source_baseline_sha256": BASELINE_HASHES,
                "scientific_equality": True,
                "diagnostic_continuation_only": True,
                "decision_promotion_allowed": False,
            })
        verified = verify_rebound_baseline()
        print({"baseline_rebound": True, "result_sha256": verified["result_sha256"],
               "bundle_sha256": verified["bundle_sha256"]})
    except Exception as exc:
        try:
            publish_technical_stop(stage, stop_code="baseline_provenance_rebind_failure",
                                   failed_gate="exact_baseline_scientific_equality",
                                   error=exc, job_id="baseline_rebind",
                                   elapsed_sec=time.monotonic() - started)
        except Exception as publish_error:
            print({"baseline_error": str(exc), "publication_error": str(publish_error)},
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
