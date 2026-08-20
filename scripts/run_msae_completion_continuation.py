#!/usr/bin/env python3
"""Provenance-only adapter for frozen atlas-completion diagnostic workers."""
from __future__ import annotations
import argparse
import importlib
import sys
import time
from pathlib import Path
from typing import Any

import msa_completion_common as base_common
from msa_completion_continuation_common import (
    CONFIG, JOBS, RUN_ROOT, STABILITY_SHARDS, canonical_job_specs,
    attest_old_raw_inputs, continuation_firewall, load_old_raw, prevalidate_old_raw,
    publish_launch_failure, publish_technical_stop, require_continuation_config,
    terminal_state, verify_continuation_freeze, verify_rebound_baseline,
    verify_source_inventory,
)

TARGETS = {
    "k2": "run_msae_refit_worker",
    "stability": "run_msae_stability",
    "specificity": "run_msae_specificity",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="target", required=True)
    k2 = sub.add_parser("k2")
    k2.add_argument("--job", choices=JOBS, required=True)
    k2_group = k2.add_mutually_exclusive_group(required=True)
    k2_group.add_argument("--point", action="store_true")
    k2_group.add_argument("--draw-start", type=int)
    k2.add_argument("--draw-end", type=int)
    k2.add_argument("--device", choices=["cuda:0"], required=True)
    stability = sub.add_parser("stability")
    stability_group = stability.add_mutually_exclusive_group(required=True)
    stability_group.add_argument("--point", action="store_true")
    stability_group.add_argument("--draw-start", type=int)
    stability.add_argument("--draw-end", type=int)
    stability.add_argument("--device", choices=["cuda:0"], required=True)
    specificity = sub.add_parser("specificity")
    specificity.add_argument("--job", choices=JOBS, required=True)
    specificity.add_argument("--device", choices=["cuda:0"], required=True)
    args = parser.parse_args(argv)
    if args.target == "k2":
        if args.point:
            if args.draw_end is not None:
                parser.error("point cannot have --draw-end")
        elif (args.draw_start, args.draw_end) != (0, 500):
            parser.error("K2 draw job must be exactly [0,500)")
    if args.target == "stability":
        if args.point:
            if args.draw_end is not None:
                parser.error("point cannot have --draw-end")
        elif (args.draw_start, args.draw_end) not in STABILITY_SHARDS:
            parser.error("stability draw job is not a registered shard")
    return args


def resolve(args: argparse.Namespace) -> tuple[str, Path, list[str], list[int]]:
    config = str(CONFIG)
    if args.target == "k2":
        short = args.job.split("_")[3]
        stage = RUN_ROOT / "k2_refit" / args.job
        if args.point:
            return f"{short}_point", stage, ["--kind", "k2", "--job", args.job,
                "--point", "--device", args.device, "--config", config], list(range(500))
        return f"{short}_draws", stage, ["--kind", "k2", "--job", args.job,
            "--draw-start", "0", "--draw-end", "500", "--device", args.device,
            "--config", config], list(range(500))
    if args.target == "stability":
        stage = RUN_ROOT / "stability"
        if args.point:
            return "stability_point", stage, ["--point", "--device", args.device,
                                               "--config", config], list(range(500))
        return f"stability_{args.draw_start}_{args.draw_end}", stage, [
            "--draw-start", str(args.draw_start), "--draw-end", str(args.draw_end),
            "--device", args.device, "--config", config], list(range(500))
    short = args.job.split("_")[3]
    return f"specificity_{short}", RUN_ROOT / "specificity" / args.job, [
        "--job", args.job, "--device", args.device, "--config", config], []


def run(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    process_started = time.monotonic()
    job_id, stage, target_argv, requested = resolve(args)
    specs = canonical_job_specs()
    if job_id not in specs or stage.resolve() != (RUN_ROOT / specs[job_id]["stage"]).resolve():
        raise RuntimeError("adapter job/stage resolution mismatch")
    stage.resolve().relative_to(RUN_ROOT.resolve())
    freeze_verified = False
    verified_freeze_sha: str | None = None
    target: Any | None = None
    original_k2: Any | None = None
    raw_provenance_failed = False
    original_argv = list(sys.argv)
    original_common = {
        "default_firewall": base_common.default_firewall,
        "verify_completion_freeze": base_common.verify_completion_freeze,
        "require_frozen_completion_config": base_common.require_frozen_completion_config,
    }
    try:
        verified_freeze_sha = verify_continuation_freeze()["bundle_sha256"]
        freeze_verified = True
        verify_rebound_baseline()
        verify_source_inventory()
        for name in TARGETS.values():
            if name in sys.modules:
                raise RuntimeError(f"frozen target imported before adapter patch: {name}")
        if args.target == "k2":
            prevalidate_old_raw(["point"] if args.point else list(range(500)))
        base_common.default_firewall = continuation_firewall
        base_common.verify_completion_freeze = verify_continuation_freeze
        base_common.require_frozen_completion_config = require_continuation_config
        target = importlib.import_module(TARGETS[args.target])
        if target.default_firewall is not continuation_firewall:
            raise RuntimeError("target did not capture continuation firewall")
        if target.require_frozen_completion_config is not require_continuation_config:
            raise RuntimeError("target did not capture continuation config verifier")
        if hasattr(target, "verify_completion_freeze"):
            if target.verify_completion_freeze is not verify_continuation_freeze:
                raise RuntimeError("target did not capture continuation freeze verifier")
        if args.target == "k2":
            original_k2 = target.k2_draw

            def paired_k2(*call_args: Any, **call_kwargs: Any) -> Any:
                nonlocal raw_provenance_failed
                draw = call_args[0] if call_args else call_kwargs.get("draw")
                draw_id: int | str = "point" if draw is None else int(draw)
                try:
                    firewall = (call_args[9] if len(call_args) > 9
                                else call_kwargs.get("firewall"))
                    if firewall is None:
                        raise RuntimeError("K2 call lacks firewall argument")
                    attest_old_raw_inputs(firewall, draw_id)
                    payload = load_old_raw(draw_id)
                except Exception as exc:
                    raw_provenance_failed = True
                    publish_technical_stop(
                        stage, stop_code="paired_raw_provenance_failure",
                        failed_gate="exact_original_raw_pairing", error=exc,
                        job_id=job_id, requested_draw_ids=requested,
                        device=args.device,
                        input_attestation=getattr(target, "_FAILURE_ATTESTATION", {}),
                        elapsed_sec=time.monotonic() - process_started,
                        verified_bundle_sha256=verified_freeze_sha)
                    raise
                if "raw_result_override" in call_kwargs:
                    raise RuntimeError("unexpected preexisting raw_result_override")
                call_kwargs["raw_result_override"] = payload
                return original_k2(*call_args, **call_kwargs)

            target.k2_draw = paired_k2
        sys.argv = [str(Path(target.__file__).resolve()), *target_argv]
        target.main()
        if raw_provenance_failed:
            raise RuntimeError("raw provenance failure was caught by frozen draw loop")
        verify_continuation_freeze()
        verify_source_inventory()
    except BaseException as exc:
        # Parsing and canonical stage resolution happened before the guarded
        # work, so every launched adapter invocation has a safe new-root stage
        # even when freeze verification itself is the failing gate.  Prefer a
        # stage-local technical terminal in all such cases; the create-once root
        # launch record is only a last-resort closure if publication itself
        # fails.
        try:
            published = publish_technical_stop(
                stage,
                stop_code=f"{args.target}_continuation_unrecoverable_failure",
                failed_gate=f"{args.target}_diagnostic_continuation",
                error=exc, job_id=job_id, requested_draw_ids=requested,
                device=args.device,
                input_attestation=(getattr(target, "_FAILURE_ATTESTATION", {})
                                   if target is not None else {}),
                elapsed_sec=time.monotonic() - process_started,
                verified_bundle_sha256=verified_freeze_sha)
            if published.name == "MEASUREMENT_COMPLETE.json":
                raise RuntimeError(
                    "technical/provenance failure occurred after scientific stage completion")
        except BaseException as publication_error:
            print({"error": str(exc), "publication_error": str(publication_error)},
                  file=sys.stderr)
            try:
                publish_launch_failure(job_id=job_id, error=publication_error,
                                       device=args.device)
            except BaseException as launch_publication_error:
                print({"launch_publication_error": str(launch_publication_error)},
                      file=sys.stderr)
        raise
    finally:
        sys.argv = original_argv
        if target is not None and original_k2 is not None:
            target.k2_draw = original_k2
        base_common.default_firewall = original_common["default_firewall"]
        base_common.verify_completion_freeze = original_common["verify_completion_freeze"]
        base_common.require_frozen_completion_config = original_common["require_frozen_completion_config"]
        for name in TARGETS.values():
            sys.modules.pop(name, None)


def main() -> None:
    run()


if __name__ == "__main__":
    main()
