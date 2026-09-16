#!/usr/bin/env python3
"""Immutable post-M1 controller for the exposed-source MSAE v3 protocol.

The M1 overlap audit succeeded with the exact base-builder bytes pinned below.
This controller authenticates that success, applies the prospectively registered
AMALGUM legacy-UPOS repair, and builds all seven M2 outputs transactionally.
Every later command enters through this file and is delegated to the separately
closed post-M1 runtime, so this scientifically material M2 controller need not be
edited after its create-once task manifest has bound it.
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import msae_independent_measurement_v3 as base

BASE_M1_SHA256 = "2d08f380998c796852b19ed2214ec77c212948fb9d1758674ea1b9895dd032bd"
M0_COMPLETION_SHA256 = "d370bb8eea01ba2cdbd1c5868a73f56f8e8a9425f3b0cc06af01e8e39181dce0"
CONTINUATION_RFC = ROOT / "docs/rfc-msae-independent-measurement-v3-m2-continuation.md"
CONTINUATION_TEST = ROOT / "tests/test_msae_independent_measurement_v3_post_m1.py"
CONTROLLER_PATH = Path(__file__)
M1_COMPLETION_PATH = base.V3_PROV / "m1_completion_manifest.json"
M2_TRANSACTION_ROOT = base.V3_PROV / ".m2_install_transaction"
RUNTIME_PATH = ROOT / "scripts/msae_independent_measurement_v3_post_m1_runtime.py"
RAW_LEGACY_TAGS = frozenset({"''", ".", "``"})

if base.sha_file(Path(base.__file__)) != BASE_M1_SHA256:
    raise RuntimeError("reviewed/successful M1 builder bytes drifted")
if base.sha_file(base.V3_DATA / "m0_completion_manifest.json") != M0_COMPLETION_SHA256:
    raise RuntimeError("reviewed M0 completion pin drifted")

LEXICAL_EXCEPTIONS = {
    ("''", "'d", "will", "xcomp"): "AUX",
    ("``", "’", "'s", "case"): "PART",
}
EXPECTED_TRANSITIONS = {
    "raw_selected": {("''", "AUX"): 1, ("''", "PUNCT"): 18,
                     (".", "PUNCT"): 11, ("``", "PART"): 1,
                     ("``", "PUNCT"): 4, ("``", "SYM"): 1},
    "tokenizable": {("''", "AUX"): 1, ("''", "PUNCT"): 7,
                    (".", "PUNCT"): 6, ("``", "PART"): 1,
                    ("``", "PUNCT"): 4, ("``", "SYM"): 1},
    "retained_after_cap": {("''", "AUX"): 1, ("''", "PUNCT"): 3,
                           (".", "PUNCT"): 3, ("``", "PART"): 1,
                           ("``", "PUNCT"): 3},
}
EXPECTED_CORRECTION_COUNTS = {"raw_selected": 36, "tokenizable": 20,
                              "retained_after_cap": 11}
EXPECTED_POPULATION_COUNTS = {"raw_selected": 290192, "tokenizable": 286938,
                              "retained_after_cap": 89600}

_original_base_labels = base._base_labels
_original_amalgum_base_rows = base._amalgum_base_rows
_original_install_json = base.install_json
_active_correction_audit: dict[str, Any] | None = None
_active_reviewed_m1_sha256: str | None = None


def corrected_upos(form: str, raw_upos: str, *, lemma: str | None = None,
                   deprel: str | None = None) -> str:
    """Apply the complete, AMALGUM-only lexical/Unicode correction registry."""
    if raw_upos in base.UPOS:
        return raw_upos
    if raw_upos not in RAW_LEGACY_TAGS or not form:
        raise ValueError(f"unregistered AMALGUM legacy UPOS value: {raw_upos!r}/{form!r}")
    exception = LEXICAL_EXCEPTIONS.get((raw_upos, form, lemma, deprel))
    categories = {unicodedata.category(char)[0] for char in form if not char.isspace()}
    if exception is not None:
        return exception
    if categories and categories <= {"P"}:
        return "PUNCT"
    if categories and categories <= {"S"}:
        return "SYM"
    raise ValueError(f"legacy UPOS repair is not punctuation/symbol-only: {raw_upos!r}/{form!r}")


def _corrected_base_labels(form: str, lemma: str, j: int, n: int,
                           **kwargs: Any) -> dict[str, str | None]:
    upos = kwargs.get("upos")
    source_genre = kwargs.get("source_genre")
    if isinstance(upos, str) and upos not in base.UPOS and upos != "__DROP__":
        if not isinstance(source_genre, str) or not source_genre.startswith("AMALGUM:"):
            # Preserve the base builder's strict failure for every non-AMALGUM source.
            return _original_base_labels(form, lemma, j, n, **kwargs)
        kwargs["upos"] = corrected_upos(form, upos, lemma=lemma,
                                         deprel=kwargs.get("deprel"))
    return _original_base_labels(form, lemma, j, n, **kwargs)


def _transition_counts(entries: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], int]:
    return dict(collections.Counter((str(item["raw_upos"]), str(item["corrected_upos"]))
                                    for item in entries))


def _ledger(stage: str, entries: list[dict[str, Any]], population_token_count: int,
            population_row_ids: Iterable[str]) -> dict[str, Any]:
    entries.sort(key=lambda item: (item["role"], item["path"].encode("utf-8"),
                                   item["sentence_id"].encode("utf-8"), item["word_index"]))
    row_ids = sorted(set(population_row_ids), key=lambda value: value.encode("utf-8"))
    if len(row_ids) != population_token_count:
        raise ValueError(f"{stage} AMALGUM population contains duplicate row identities")
    if population_token_count != EXPECTED_POPULATION_COUNTS[stage]:
        raise ValueError(f"{stage} AMALGUM population denominator drift: {population_token_count}")
    transitions = _transition_counts(entries)
    if len(entries) != EXPECTED_CORRECTION_COUNTS[stage] or transitions != EXPECTED_TRANSITIONS[stage]:
        raise ValueError(f"{stage} legacy-UPOS correction inventory drift: {len(entries)}/{transitions}")
    return {
        "stage": stage,
        "population_definition": {
            "raw_selected": "all integer-token rows in the frozen selected AMALGUM partition",
            "tokenizable": "raw-selected token rows in sentences accepted by the frozen local tokenizer and length rule",
            "retained_after_cap": "tokenizable rows retained by the frozen deterministic 256-row-per-document cap and used by support/maps",
        }[stage],
        "population_token_count": population_token_count,
        "population_row_id_set_sha256": base.sha_bytes(base.canonical_bytes(row_ids)),
        "correction_token_count": len(entries),
        "transition_counts": [
            {"raw_upos": raw, "corrected_upos": corrected, "token_count": count}
            for (raw, corrected), count in sorted(transitions.items())
        ],
        "correction_entries": entries,
        "correction_entries_sha256": base.sha_bytes(base.canonical_bytes(entries)),
    }


def _corrected_amalgum_base_rows(tokenizer: Any,
                                 prefix_ids: Sequence[Sequence[int]]) -> dict[str, list[dict[str, Any]]]:
    """Build rows and close raw/tokenizable/retained correction provenance."""
    global _active_correction_audit
    by_role = _original_amalgum_base_rows(tokenizer, prefix_ids)
    tokenizable_ids = {role: {str(row["row_id"]) for row in rows}
                       for role, rows in by_role.items()}
    retained = {role: base._cap_rows(rows) for role, rows in by_role.items()}
    retained_ids = {role: {str(row["row_id"]) for row in rows}
                    for role, rows in retained.items()}

    partition = base.read_json(
        ROOT / "data/msae_independent_measurement_v1/source_partition.json")
    raw_population_ids: list[str] = []
    raw_entries: list[dict[str, Any]] = []
    for item in partition["selected"]:
        role = item["role"]
        if role not in {"C1", "C2"}:
            raise ValueError(f"unexpected selected AMALGUM role: {role!r}")
        path = ROOT / "data/msae_independent_measurement_v1/selected_raw" / item["path"]
        documents = base.parse_conllu(path, strict_entities=True)
        if len(documents) != 1:
            raise ValueError(f"selected AMALGUM file must contain exactly one document: {path}")
        for sentence in documents[0]["sentences"]:
            for j, token in enumerate(sentence["tokens"]):
                row_id = f"{item['path']}:{sentence['sentence_id']}:{j}"
                raw_population_ids.append(row_id)
                raw_upos = token["upos"]
                if raw_upos in base.UPOS:
                    continue
                corrected = corrected_upos(token["form"], raw_upos,
                                            lemma=token["lemma"], deprel=token["deprel"])
                raw_entries.append({
                    "role": role, "path": item["path"],
                    "sentence_id": sentence["sentence_id"], "word_index": j,
                    "row_id": row_id, "form": token["form"], "lemma": token["lemma"],
                    "deprel": token["deprel"], "raw_upos": raw_upos,
                    "corrected_upos": corrected,
                })

    tokenizable_entries = [dict(item) for item in raw_entries
                           if item["row_id"] in tokenizable_ids[item["role"]]]
    retained_entries = [dict(item) for item in raw_entries
                        if item["row_id"] in retained_ids[item["role"]]]
    _active_correction_audit = {
        "schema_version": "msae_v3_amalgum_legacy_upos_audit_v1",
        "population_transition": ["raw_selected", "tokenizable", "retained_after_cap"],
        "ledgers": {
            "raw_selected": _ledger("raw_selected", raw_entries, len(raw_population_ids),
                                    raw_population_ids),
            "tokenizable": _ledger(
                "tokenizable", tokenizable_entries, sum(len(rows) for rows in by_role.values()),
                (str(row["row_id"]) for rows in by_role.values() for row in rows)),
            "retained_after_cap": _ledger(
                "retained_after_cap", retained_entries,
                sum(len(rows) for rows in retained.values()),
                (str(row["row_id"]) for rows in retained.values() for row in rows)),
        },
    }
    _active_correction_audit["audit_sha256"] = base.sha_bytes(
        base.canonical_bytes(_active_correction_audit))
    return by_role


def _m1_artifact_entries() -> list[dict[str, Any]]:
    return [base._content_entry(base.V3_DATA / name)
            for name in base.V3_DATA_PHASE_FILES["M1"]]


def _validate_m1_success_semantics() -> dict[str, Any]:
    alias = base.read_json(base.V3_DATA / "source_alias_manifest.json")
    fixtures = base.read_json(base.V3_DATA / "overlap_fixtures.json")
    overlap = base.read_json(base.V3_DATA / "history_overlap.json")
    crosswalk = base.read_json(base.V3_DATA / "v1_row_crosswalk.json")
    expected = {
        "source_alias_selected_count": 350,
        "fixture_count": 40,
        "fixture_status": "eligible",
        "historical_documents": 23658,
        "candidate_pairs": 8297,
        "idf_universe_documents": 24008,
        "overlap_status": "eligible",
        "blocking_collision_count": 0,
        "sealed_payload_content_reads": 0,
        "legacy_crosswalk_rows": 206,
        "legacy_crosswalk_status": "ineligible",
    }
    observed = {
        "source_alias_selected_count": alias.get("selected_count"),
        "fixture_count": fixtures.get("fixture_count"),
        "fixture_status": fixtures.get("status"),
        # The two census-only counts are checked against the canonical prefix
        # below; copying the registered values here makes the combined semantic
        # assertion explicit without materializing the 1.85 GB census JSON.
        "historical_documents": 23658,
        "candidate_pairs": 8297,
        "idf_universe_documents": overlap.get("idf_universe_documents"),
        "overlap_status": overlap.get("status"),
        "blocking_collision_count": overlap.get("blocking_collision_count"),
        "sealed_payload_content_reads": overlap.get("sealed_payload_content_reads"),
        "legacy_crosswalk_rows": crosswalk.get("legacy_row_count"),
        "legacy_crosswalk_status": crosswalk.get("legacy_status"),
    }
    if observed != expected:
        raise ValueError(f"successful M1 semantic assertion drift: {observed!r}")
    # The 1.85 GB census is content-bound below.  Verify its small, canonical
    # top-level scalar prefix/suffix without materializing it a second time.
    census_path = base.V3_DATA / "history_census.json"
    with census_path.open("rb") as handle:
        prefix = handle.read(512)
        handle.seek(max(0, census_path.stat().st_size - 512))
        suffix = handle.read()
    expected_prefix = (b'{"adapter_document_counts":{"conllu":11697,"diff":1,"jsonl":11956,"md":4},'
                       b'"candidate_pairs":8297,"historical_documents":23658,'
                       b'"idf_universe_documents":24008,')
    expected_suffix = (b'"schema_version":"msae_v3_history_census_v1",'
                       b'"sealed_payload_content_reads":0,"selected_documents":350}\n')
    if not prefix.startswith(expected_prefix) or not suffix.endswith(expected_suffix):
        raise ValueError("successful M1 history-census scalar semantics drift")
    return expected


def _m1_completion_payload() -> dict[str, Any]:
    entries = _m1_artifact_entries()
    return {
        "schema_version": "msae_v3_m1_completion_manifest_v1",
        "protocol_id": base.PROTOCOL,
        "reviewed_m1_builder_sha256": BASE_M1_SHA256,
        "reviewed_m0_completion_sha256": M0_COMPLETION_SHA256,
        "entries": entries,
        "entry_count": len(entries),
        "entries_sha256": base.sha_bytes(base.canonical_bytes(entries)),
        "success_semantics": _validate_m1_success_semantics(),
        "status": "m1_overlap_eligible_ready_for_independent_review_pin",
    }


def build_m1_completion() -> dict[str, Any]:
    """Create the independent-review input pin; this command performs no M2 work."""
    base.verify_m0_completion(M0_COMPLETION_SHA256, projection_phase="M1")
    if M2_TRANSACTION_ROOT.exists() or any((base.V3_DATA / name).exists()
                                           for name in base.V3_DATA_PHASE_FILES["M2"]):
        raise ValueError("M1 completion pin must precede every M2 output")
    payload = _m1_completion_payload()
    base.write_once(M1_COMPLETION_PATH, base.canonical_bytes(payload), 0o644)
    if M1_COMPLETION_PATH.read_bytes() != base.canonical_bytes(payload):
        raise AssertionError("M1 completion installed-byte mismatch")
    return payload


@contextlib.contextmanager
def _m2_recovery_projection() -> Iterable[None]:
    """Allow only declared M2 targets while revalidating completed M0+M1."""
    original = base._phase_data_names

    def phase_names(phase: str) -> set[str]:
        names = original(phase)
        if phase == "M1":
            names |= {name for name in base.V3_DATA_PHASE_FILES["M2"]
                      if (base.V3_DATA / name).exists()}
        return names

    base._phase_data_names = phase_names
    try:
        yield
    finally:
        base._phase_data_names = original


def _recovery_state_is_declared() -> bool:
    targets = {name for name in base.V3_DATA_PHASE_FILES["M2"]
               if (base.V3_DATA / name).exists()}
    if not targets:
        return M2_TRANSACTION_ROOT.exists()
    if M2_TRANSACTION_ROOT.exists():
        return True
    return targets == set(base.V3_DATA_PHASE_FILES["M2"])


def verify_m1_completion(expected_sha256: str, *, allow_m2_recovery: bool = False) -> dict[str, Any]:
    base.validate_sha256(expected_sha256, "reviewed successful-M1 completion SHA-256")
    if base.sha_file(M1_COMPLETION_PATH) != expected_sha256:
        raise ValueError("reviewed successful-M1 completion digest mismatch")
    if allow_m2_recovery:
        if not _recovery_state_is_declared():
            raise ValueError("partial M2 outputs exist without a recovery transaction")
        with _m2_recovery_projection():
            base.verify_m0_completion(M0_COMPLETION_SHA256, projection_phase="M1")
    else:
        base.verify_m0_completion(M0_COMPLETION_SHA256, projection_phase="M1")
    observed = base.read_json(M1_COMPLETION_PATH)
    expected = _m1_completion_payload()
    if observed != expected or M1_COMPLETION_PATH.read_bytes() != base.canonical_bytes(observed):
        raise ValueError("successful-M1 completion semantic/canonical mismatch")
    return observed


def continuation_closure_entries(extra_paths: Sequence[Path] = ()) -> list[dict[str, Any]]:
    """Return the mandatory closure extension used by every post-M1 runtime."""
    paths = [CONTROLLER_PATH, CONTINUATION_RFC, CONTINUATION_TEST, M1_COMPLETION_PATH]
    paths.extend(extra_paths)
    entries = [base._content_entry(path) for path in paths]
    relative = [str(item["path"]) for item in entries]
    if len(relative) != len(set(relative)):
        raise ValueError("duplicate post-M1 closure path")
    return sorted(entries, key=lambda item: str(item["path"]).encode("utf-8"))


def extend_closure_payload(payload: Mapping[str, Any],
                           extra_paths: Sequence[Path] = ()) -> dict[str, Any]:
    """Add immutable continuation bytes to a base closure without replacement."""
    result = dict(payload)
    entries = list(result.get("entries", []))
    by_path = {str(item["path"]): item for item in entries}
    if len(by_path) != len(entries):
        raise ValueError("duplicate base closure path")
    for item in continuation_closure_entries(extra_paths):
        path = str(item["path"])
        if path in by_path and by_path[path] != item:
            raise ValueError(f"post-M1 closure conflicts with base entry: {path}")
        by_path[path] = item
    result["entries"] = sorted(by_path.values(), key=lambda item: str(item["path"]).encode("utf-8"))
    result["post_m1_continuation_entry_count"] = len(continuation_closure_entries(extra_paths))
    result["post_m1_continuation_entries_sha256"] = base.sha_bytes(
        base.canonical_bytes(continuation_closure_entries(extra_paths)))
    return result


def _continuation_binding() -> dict[str, Any]:
    if _active_reviewed_m1_sha256 is None:
        raise RuntimeError("no reviewed successful-M1 pin is active")
    entries = continuation_closure_entries()
    return {
        "schema_version": "msae_v3_post_m1_continuation_binding_v2",
        "entries": entries,
        "entries_sha256": base.sha_bytes(base.canonical_bytes(entries)),
        "reviewed_m1_builder_sha256": BASE_M1_SHA256,
        "reviewed_m0_completion_sha256": M0_COMPLETION_SHA256,
        "reviewed_successful_m1_completion_sha256": _active_reviewed_m1_sha256,
        "later_phase_entrypoint": str(Path(__file__).relative_to(ROOT)),
        "later_phase_runtime_rule": "controller_delegates_and_runtime_must_extend_closure_with_its_current_bytes",
    }


def _install_with_continuation(path: Path, value: Any) -> None:
    if path == base.V3_DATA / "task_manifest.json":
        if _active_correction_audit is None:
            raise RuntimeError("AMALGUM correction audit was not constructed")
        value = dict(value)
        value["post_m1_continuation"] = _continuation_binding()
        value["amalgum_legacy_upos_repair"] = {
            "policy": "AMALGUM_only_exact_exceptions_then_all_P_to_PUNCT_or_all_S_to_SYM",
            "registered_raw_tags": sorted(RAW_LEGACY_TAGS),
            "lexical_exception_registry": [
                {"raw_upos": raw, "form": form, "lemma": lemma, "deprel": deprel,
                 "corrected_upos": corrected}
                for (raw, form, lemma, deprel), corrected in sorted(LEXICAL_EXCEPTIONS.items())
            ],
            "unknown_mixed_or_non_AMALGUM": "blocking",
            "audit": _active_correction_audit,
        }
    elif path == base.V3_DATA / "protocol_imports.json":
        value = dict(value)
        value["post_m1_continuation"] = _continuation_binding()
    _original_install_json(path, value)


def _verify_staging_projection(stage_data: Path) -> None:
    expected = set(base.V3_DATA_PHASE_FILES["M2"])
    observed = {entry.name for entry in os.scandir(stage_data)}
    if observed != expected:
        raise ValueError(f"M2 staging projection mismatch: {sorted(observed ^ expected)}")
    for name in expected:
        path = stage_data / name
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o644:
            raise ValueError(f"invalid M2 staged output: {name}")


def _compute_m2_payloads(reviewed_m1_sha256: str) -> tuple[dict[str, bytes], dict[str, Any]]:
    global _active_correction_audit, _active_reviewed_m1_sha256
    real_data = base.V3_DATA
    original_verify = base.verify_baseline_projection
    original_labels = base._base_labels
    original_amalgum = base._amalgum_base_rows
    original_install = base.install_json
    _active_correction_audit = None
    _active_reviewed_m1_sha256 = reviewed_m1_sha256
    with tempfile.TemporaryDirectory(prefix="msae_v3_m2_compute_") as raw_temp:
        stage_data = Path(raw_temp) / "data"
        stage_data.mkdir(mode=0o700)

        def staged_verify(phase: str) -> dict[str, Any]:
            if phase == "M1":
                # The authenticated before-compute gate was executed by the caller.
                return {"phase": "M1", "authenticated_by": "reviewed_successful_m1_completion"}
            if phase == "M2":
                _verify_staging_projection(stage_data)
                return {"phase": "M2", "staged": True}
            raise ValueError(f"unexpected staged verification phase: {phase}")

        try:
            base.V3_DATA = stage_data
            base.verify_baseline_projection = staged_verify
            base._base_labels = _corrected_base_labels
            base._amalgum_base_rows = _corrected_amalgum_base_rows
            base.install_json = _install_with_continuation
            state = base.build_labels()
            retained_ids = {role: {str(row["row_id"]) for row in state["rows_by_role"][role]}
                            for role in ("C1", "C2")}
            audited_ids = {
                item["role"]: set() for item in
                _active_correction_audit["ledgers"]["retained_after_cap"]["correction_entries"]
            } if _active_correction_audit is not None else {}
            if _active_correction_audit is None:
                raise RuntimeError("correction audit missing after AMALGUM row construction")
            for item in _active_correction_audit["ledgers"]["retained_after_cap"]["correction_entries"]:
                audited_ids.setdefault(item["role"], set()).add(item["row_id"])
            if any(not ids <= retained_ids[role] for role, ids in audited_ids.items()):
                raise AssertionError("retained correction ledger is not a subset of support/map rows")
            matrix = base.build_maps(state)
            base.build_protocol_imports()
            _verify_staging_projection(stage_data)
            payloads = {name: (stage_data / name).read_bytes()
                        for name in base.V3_DATA_PHASE_FILES["M2"]}
        finally:
            base.install_json = original_install
            base._amalgum_base_rows = original_amalgum
            base._base_labels = original_labels
            base.verify_baseline_projection = original_verify
            base.V3_DATA = real_data
    return payloads, matrix


def _ensure_m2_transaction_parent() -> None:
    parent = M2_TRANSACTION_ROOT.parent
    st = parent.lstat()
    if (not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
            or stat.S_IMODE(st.st_mode) != 0o700 or st.st_uid != os.getuid()):
        raise ValueError("invalid M2 provenance directory")


def _install_m2_transaction(payloads: Mapping[str, bytes]) -> None:
    expected_names = set(base.V3_DATA_PHASE_FILES["M2"])
    if set(payloads) != expected_names:
        raise ValueError("M2 transaction payload set mismatch")
    target_state = {name: (base.V3_DATA / name).exists() for name in expected_names}
    if not M2_TRANSACTION_ROOT.exists() and any(target_state.values()):
        if not all(target_state.values()):
            raise ValueError("orphaned partial M2 outputs without recovery transaction")
        for name, payload in payloads.items():
            path = base.V3_DATA / name
            st = path.lstat()
            if (not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)
                    or stat.S_IMODE(st.st_mode) != 0o644 or path.read_bytes() != payload):
                raise ValueError(f"completed M2 output drift: {name}")
        return
    _ensure_m2_transaction_parent()
    if not M2_TRANSACTION_ROOT.exists():
        M2_TRANSACTION_ROOT.mkdir(mode=0o700)
        os.chmod(M2_TRANSACTION_ROOT, 0o700)
        base._fsync_directory(M2_TRANSACTION_ROOT.parent)
    st = M2_TRANSACTION_ROOT.lstat()
    if (not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode)
            or stat.S_IMODE(st.st_mode) != 0o700 or st.st_uid != os.getuid()):
        raise ValueError("invalid M2 recovery transaction directory")
    allowed = {"transaction.json"} | {
        f"{ordinal:02d}.{name}.payload"
        for ordinal, name in enumerate(base.V3_DATA_PHASE_FILES["M2"])
    }
    observed = {entry.name for entry in os.scandir(M2_TRANSACTION_ROOT)}
    if observed - allowed:
        raise ValueError(f"undeclared M2 transaction entries: {sorted(observed - allowed)}")
    entries = []
    for ordinal, name in enumerate(base.V3_DATA_PHASE_FILES["M2"]):
        payload = payloads[name]
        staged_name = f"{ordinal:02d}.{name}.payload"
        staged = M2_TRANSACTION_ROOT / staged_name
        if staged.exists():
            staged_st = staged.lstat()
            if (not stat.S_ISREG(staged_st.st_mode) or stat.S_ISLNK(staged_st.st_mode)
                    or stat.S_IMODE(staged_st.st_mode) != 0o600 or staged.read_bytes() != payload):
                raise ValueError(f"M2 staged recovery payload drift: {name}")
        else:
            base.write_once(staged, payload, 0o600)
        entries.append({"name": name, "staged_name": staged_name, "size": len(payload),
                        "sha256": base.sha_bytes(payload), "target_mode": 0o644})
    descriptor = base.canonical_bytes({
        "schema_version": "msae_v3_m2_recoverable_install_v1",
        "protocol_id": base.PROTOCOL, "entries": entries, "entry_count": len(entries),
        "payload_set_sha256": base.sha_bytes(base.canonical_bytes(entries)),
    })
    descriptor_path = M2_TRANSACTION_ROOT / "transaction.json"
    if descriptor_path.exists():
        if (descriptor_path.is_symlink() or descriptor_path.read_bytes() != descriptor
                or stat.S_IMODE(descriptor_path.stat().st_mode) != 0o600):
            raise ValueError("M2 transaction descriptor drift")
    else:
        base.write_once(descriptor_path, descriptor, 0o600)
    base._fsync_directory(M2_TRANSACTION_ROOT)
    for name in base.V3_DATA_PHASE_FILES["M2"]:
        target = base.V3_DATA / name
        payload = payloads[name]
        if target.exists():
            target_st = target.lstat()
            if (not stat.S_ISREG(target_st.st_mode) or stat.S_ISLNK(target_st.st_mode)
                    or stat.S_IMODE(target_st.st_mode) != 0o644 or target.read_bytes() != payload):
                raise ValueError(f"M2 target drift during recovery: {name}")
        else:
            base.write_once(target, payload, 0o644)
    base._fsync_directory(base.V3_DATA)
    for name, payload in payloads.items():
        target = base.V3_DATA / name
        if target.read_bytes() != payload or base.sha_file(target) != base.sha_bytes(payload):
            raise AssertionError(f"M2 installed-byte verification failed: {name}")
    descriptor_path.unlink()
    for entry in entries:
        (M2_TRANSACTION_ROOT / entry["staged_name"]).unlink()
    M2_TRANSACTION_ROOT.rmdir()
    base._fsync_directory(M2_TRANSACTION_ROOT.parent)


def build_labels_maps(reviewed_m1_sha256: str) -> dict[str, Any]:
    """Compute all M2 bytes off-tree, reauthenticate M1, then install atomically."""
    recovering = M2_TRANSACTION_ROOT.exists() or any(
        (base.V3_DATA / name).exists() for name in base.V3_DATA_PHASE_FILES["M2"])
    verify_m1_completion(reviewed_m1_sha256, allow_m2_recovery=recovering)
    payloads, matrix = _compute_m2_payloads(reviewed_m1_sha256)
    verify_m1_completion(reviewed_m1_sha256, allow_m2_recovery=recovering)
    _install_m2_transaction(payloads)
    base.verify_baseline_projection("M2")
    return matrix


def __getattr__(name: str) -> Any:
    return getattr(base, name)


def main(argv: Sequence[str] | None = None) -> None:
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        raise SystemExit("a command is required")
    if raw[0] == "build-m1-completion":
        if len(raw) != 1:
            raise SystemExit("build-m1-completion accepts no arguments")
        print(json.dumps(build_m1_completion(), indent=2))
        return
    if raw[0] == "build-labels-maps":
        parser = argparse.ArgumentParser()
        parser.add_argument("command")
        parser.add_argument("--reviewed-m1-sha256", required=True)
        args = parser.parse_args(raw)
        print(json.dumps(build_labels_maps(args.reviewed_m1_sha256), indent=2))
        return
    # Every later phase must enter through this immutable controller.  The
    # mutable runtime is required to add its own current bytes to the closure.
    from msae_independent_measurement_v3_post_m1_runtime import dispatch
    dispatch(raw)


if __name__ == "__main__":
    main()
