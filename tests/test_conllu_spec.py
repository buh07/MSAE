from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import pytest

from scripts.conllu_spec import ConlluError, TokenId, parse_bytes, validate_unique_sent_ids
from scripts.validate_opened_conllu import build_report


def doc(rows: list[str], *, sent_id: str = "s1", text: str = "Example") -> bytes:
    return (f"# sent_id = {sent_id}\n# text = {text}\n" + "\n".join(rows) + "\n\n").encode()


ROOT = "1\tRoot\troot\tNOUN\t_\t_\t0\troot\t0:root\t_"
CHILD = "2\tchild\tchild\tNOUN\t_\tNumber=Sing\t1\tnmod\t1:nmod\t_"


def error_code(data: bytes, profile: str = "strict") -> str:
    with pytest.raises(ConlluError) as exc:
        parse_bytes(data, profile=profile)  # type: ignore[arg-type]
    return exc.value.code


def test_basic_sentence_and_clean_eof_profiles() -> None:
    parsed = parse_bytes(doc([ROOT, CHILD]))
    assert parsed.sentences[0].sent_id == "s1"
    clean_eof = doc([ROOT, CHILD]).rstrip(b"\n")
    assert error_code(clean_eof) == "FINAL_BLANK"
    reader = parse_bytes(clean_eof, profile="reader")
    assert reader.deviations == ("CLEAN_EOF_ACCEPTED",)


def test_crlf_is_strict_error_and_reader_deviation() -> None:
    crlf = doc([ROOT, CHILD]).replace(b"\n", b"\r\n")
    assert error_code(crlf) == "LINE_ENDING"
    assert parse_bytes(crlf, profile="reader").deviations == ("CRLF_NORMALIZED",)


def test_sentence_initial_empty_node_0_1() -> None:
    empty = "0.1\tThere\tthere\tPRON\t_\t_\t_\t_\t1:expl\t_"
    parsed = parse_bytes(doc([empty, ROOT, CHILD]))
    assert parsed.sentences[0].rows[0].id == TokenId(0, 1)


def test_sentence_initial_empty_suffix_must_be_consecutive() -> None:
    empty = "0.2\tThere\tthere\tPRON\t_\t_\t_\t_\t1:expl\t_"
    assert error_code(doc([empty, ROOT])) == "EMPTY_SUFFIX"


def test_ordinary_empty_nodes_and_i10_typed_deps_order() -> None:
    empties = [
        f"1.{i}\te{i}\te{i}\tX\t_\t_\t_\t_\t1:dep\t_" for i in range(1, 11)
    ]
    token2 = "2\tx\tx\tX\t_\t_\t1\tdep\t1.9:dep|1.10:dep\t_"
    parsed = parse_bytes(doc([ROOT, *empties, token2]))
    assert len(parsed.sentences[0].rows) == 12


def test_deps_decimal_lexicographic_misorder_rejected() -> None:
    empties = [f"1.{i}\te{i}\te{i}\tX\t_\t_\t_\t_\t1:dep\t_" for i in range(1, 11)]
    bad = "2\tx\tx\tX\t_\t_\t1\tdep\t1.10:dep|1.9:dep\t_"
    assert error_code(doc([ROOT, *empties, bad])) == "DEPS_ORDER"


def test_empty_node_must_immediately_follow_base() -> None:
    empty = "1.1\te\te\tX\t_\t_\t_\t_\t1:dep\t_"
    assert error_code(doc([ROOT, CHILD, empty])) == "EMPTY_POSITION"


def test_multiword_range_and_typo_exception() -> None:
    mwt = "1-2\tcan't\t_\t_\t_\tTypo=Yes\t_\t_\t_\tSpaceAfter=No"
    first = "1\tca\tcan\tAUX\t_\t_\t2\taux\t2:aux\t_"
    root = "2\tn't\tnot\tPART\t_\t_\t0\troot\t0:root\t_"
    assert len(parse_bytes(doc([mwt, first, root])).sentences) == 1


@pytest.mark.parametrize("feats", ["Number=Sing", "Typo=No", "Typo=Yes|X=Y"])
def test_multiword_invalid_feats(feats: str) -> None:
    mwt = f"1-2\tcan't\t_\t_\t_\t{feats}\t_\t_\t_\t_"
    assert error_code(doc([mwt, ROOT, CHILD])) == "MWT_FEATS"


def test_overlapping_or_misplaced_range_rejected() -> None:
    mwt = "2-3\tab\t_\t_\t_\t_\t_\t_\t_\t_"
    assert error_code(doc([mwt, ROOT, CHILD])) == "MWT_POSITION"


@pytest.mark.parametrize(
    "bad_id",
    ["0", "01", "1.", ".1", "1-1", "2-1", "x", "1.0", "-1"],
)
def test_malformed_ids(bad_id: str) -> None:
    row = ROOT.replace("1\t", f"{bad_id}\t", 1)
    assert error_code(doc([row])) in {"ID_MALFORMED", "ID_RANGE_ORDER"}


def test_integer_ids_are_consecutive() -> None:
    third = CHILD.replace("2\t", "3\t", 1)
    assert error_code(doc([ROOT, third])) == "ID_NONCONSECUTIVE"


def test_missing_sentence_separator_detected() -> None:
    data = doc([ROOT]).rstrip(b"\n") + b"\n# sent_id = s2\n# text = second\n" + ROOT.encode() + b"\n\n"
    assert error_code(data) == "COMMENT_AFTER_DATA"


def test_leading_and_repeated_blank_lines_rejected() -> None:
    assert error_code(b"\n" + doc([ROOT])) == "EXTRA_BLANK"
    assert error_code(doc([ROOT]) + b"\n" + doc([ROOT], sent_id="s2")) == "EXTRA_BLANK"


def test_empty_node_for_prior_token_cannot_follow_next_mwt_range() -> None:
    token7 = ROOT.replace("1\t", "7\t", 1)
    # Build a valid prefix 1..7 with token 7 as the root.
    prefix = [f"{i}\tw{i}\tw{i}\tX\t_\t_\t7\tdep\t7:dep\t_" for i in range(1, 7)] + [token7]
    mwt = "8-9\tab\t_\t_\t_\t_\t_\t_\t_\t_"
    empty = "7.1\te\te\tX\t_\t_\t_\t_\t7:dep\t_"
    eight = "8\ta\ta\tX\t_\t_\t7\tdep\t7:dep\t_"
    nine = "9\tb\tb\tX\t_\t_\t7\tdep\t7:dep\t_"
    assert error_code(doc([*prefix, mwt, empty, eight, nine])) == "EMPTY_AFTER_MWT"


def test_partial_row_and_partial_header_detected() -> None:
    assert error_code(b"# sent_id = s1\n# text = x\n1\tx\n\n") == "COLUMN_COUNT"
    assert error_code(b"# sent_id\n# text = x\n" + ROOT.encode() + b"\n\n") == "SENT_ID_HEADER"


def test_missing_or_duplicate_required_metadata() -> None:
    assert error_code(b"# text = x\n" + ROOT.encode() + b"\n\n") == "SENT_ID_COUNT"
    duplicate = b"# sent_id = a\n# sent_id = b\n# text = x\n" + ROOT.encode() + b"\n\n"
    assert error_code(duplicate) == "SENT_ID_COUNT"


def test_sent_id_has_no_whitespace_and_prefix_comment_is_unrestricted() -> None:
    bad = b"# sent_id = has space\n# text = x\n" + ROOT.encode() + b"\n\n"
    assert error_code(bad) == "SENT_ID_HEADER"
    valid = b"# textual note\n# sent_id = s\n# text = x\n" + ROOT.encode() + b"\n\n"
    assert len(parse_bytes(valid).sentences) == 1
    compact = b"# sent_id=s\n# text=x\n" + ROOT.encode() + b"\n\n"
    assert parse_bytes(compact).sentences[0].sent_id == "s"
    spaced = b"#  sent_id\t =  s\n#\t text =  x\n" + ROOT.encode() + b"\n\n"
    assert parse_bytes(spaced).sentences[0].sent_id == "s"


def test_duplicate_sent_id_in_file_and_manifest() -> None:
    same_file = doc([ROOT], sent_id="same") + doc([ROOT], sent_id="same")
    assert error_code(same_file) == "SENT_ID_DUPLICATE"
    a = parse_bytes(doc([ROOT], sent_id="same", text="a"))
    b = parse_bytes(doc([ROOT], sent_id="same", text="b"))
    with pytest.raises(ConlluError, match="SENT_ID_DUPLICATE_MANIFEST"):
        validate_unique_sent_ids([("a", a), ("b", b)])


def test_comment_after_data_rejected() -> None:
    bad = b"# sent_id = s\n# text = x\n" + ROOT.encode() + b"\n# note = late\n\n"
    assert error_code(bad) == "COMMENT_AFTER_DATA"


def test_tree_root_reference_self_and_cycle_errors() -> None:
    self_row = ROOT.replace("\t0\troot\t", "\t1\tdep\t")
    assert error_code(doc([self_row])) == "HEAD_SELF"
    absent = CHILD.replace("\t1\tnmod\t", "\t3\tnmod\t")
    assert error_code(doc([ROOT, absent])) == "HEAD_REFERENCE"
    one = ROOT.replace("\t0\troot\t", "\t2\tdep\t").replace("0:root", "2:dep")
    two = CHILD.replace("\t1\tnmod\t", "\t1\tdep\t")
    assert error_code(doc([one, two])) in {"ROOT_COUNT", "HEAD_CYCLE"}


def test_deps_reference_order_duplicate_and_shared_head_relations() -> None:
    bad_ref = CHILD.replace("1:nmod", "3:nmod")
    assert error_code(doc([ROOT, bad_ref])) == "DEPS_REFERENCE"
    bad_dup = CHILD.replace("1:nmod", "1:nmod|1:nmod")
    assert error_code(doc([ROOT, bad_dup])) == "DEPS_DUPLICATE"
    shared = CHILD.replace("1:nmod", "1:nmod|1:obl")
    assert len(parse_bytes(doc([ROOT, shared])).sentences) == 1


def test_feats_sorting_is_case_insensitive_and_misc_is_unrestricted_text() -> None:
    bad_feats = CHILD.replace("Number=Sing", "Number=Sing|Case=Nom")
    assert error_code(doc([ROOT, bad_feats])) == "FEATS_ORDER"
    valid_feats = CHILD.replace("Number=Sing", "Number=Sing|NumForm=Combi|NumType=Card")
    assert len(parse_bytes(doc([ROOT, valid_feats])).sentences) == 1
    free_misc = CHILD[:-1] + "XML=<hi rend:::bold>|odd text"
    assert len(parse_bytes(doc([ROOT, free_misc])).sentences) == 1
    bad_lower = CHILD.replace("Number=Sing", "foo=bar")
    assert error_code(doc([ROOT, bad_lower])) == "FEATS_GRAMMAR"
    bad_value_suffix = CHILD.replace("Number=Sing", "Case=Nom[foo]")
    assert error_code(doc([ROOT, bad_value_suffix])) == "FEATS_GRAMMAR"


def test_integer_upos_and_deprel_are_mandatory_and_grammatical() -> None:
    assert error_code(doc([ROOT.replace("\tNOUN\t", "\t_\t")])) == "UPOS"
    assert error_code(doc([ROOT.replace("\troot\t0:root", "\t_\t0:root")])) == "DEPREL"
    assert error_code(doc([ROOT, CHILD.replace("\tnmod\t", "\tBAD|REL\t")])) == "DEPREL"
    assert error_code(doc([ROOT, CHILD.replace("\tnmod\t", "\tref\t")])) == "DEPREL"
    assert error_code(doc([ROOT, CHILD.replace("\tnmod\t", "\tnmod:Foo:Bar\t")])) == "DEPREL"
    for relation in ("nmod:foo-1", "nmod:foo_bar", "nmod:foo:bar"):
        assert error_code(doc([ROOT, CHILD.replace("\tnmod\t", f"\t{relation}\t")])) == "DEPREL"
    enhanced_ref = CHILD.replace("1:nmod", "1:ref")
    assert len(parse_bytes(doc([ROOT, enhanced_ref])).sentences) == 1


def test_empty_node_upos_is_optional_but_validated() -> None:
    valid = "0.1\tThere\tthere\tPRON\t_\t_\t_\t_\t1:expl\t_"
    unspecified = valid.replace("\tPRON\t", "\t_\t")
    invalid = valid.replace("\tPRON\t", "\tNOT_A_UPOS\t")
    assert len(parse_bytes(doc([valid, ROOT])).sentences) == 1
    assert len(parse_bytes(doc([unspecified, ROOT])).sentences) == 1
    assert error_code(doc([invalid, ROOT])) == "UPOS"


def test_non_nfc_and_bad_utf8() -> None:
    decomposed = doc([ROOT], text="cafe\N{COMBINING ACUTE ACCENT}")
    with pytest.raises(ConlluError) as nfc:
        parse_bytes(decomposed)
    assert (nfc.value.code, nfc.value.line) == ("UNICODE_NFC", 2)
    with pytest.raises(ConlluError) as utf:
        parse_bytes(b"# note\n\xff\n\n")
    assert (utf.value.code, utf.value.line) == ("UTF8", 2)


def test_non_lf_unicode_line_separator_rejected() -> None:
    bad = doc([ROOT]).replace(b"# text = Example\n", "# text = Example\N{LINE SEPARATOR}".encode())
    assert error_code(bad) == "LINE_ENDING"


def test_partial_known_text_header() -> None:
    data = b"# sent_id = s\n# text\n" + ROOT.encode() + b"\n\n"
    assert error_code(data) == "TEXT_HEADER"


def write_manifest(path: Path, entries: list[dict[str, object]]) -> Path:
    manifest = path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": "relational_objects_v2_opened_conllu_manifest_v1",
        "expected_physical_files": len(entries),
        "scan_roots": ["data"],
        "entries": entries,
    }), encoding="utf-8")
    return manifest


def write_freeze(path: Path, manifest: Path) -> Path:
    root = Path(__file__).resolve().parents[1]
    roles = {
        "plan": root / "PLAN_RELATIONAL_OBJECTS_V2.md",
        "parser": root / "scripts/conllu_spec.py",
        "validator": root / "scripts/validate_opened_conllu.py",
        "tests": Path(__file__).resolve(),
        "profile_note": root / "docs/conllu_v2_spec_profile.md",
        "manifest": manifest,
    }
    inventory = [
        {"role": role, "path": file.as_posix(), "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
        for role, file in sorted(roles.items())
    ]
    freeze = path / "freeze.json"
    freeze.write_text(json.dumps({
        "schema_version": "relational_objects_v2_parser_validation_freeze_v1",
        "profile": "strict",
        "python_version": platform.python_version(),
        "inventory": inventory,
    }), encoding="utf-8")
    return freeze


def report_for(data_root: Path, manifest: Path) -> dict[str, object]:
    return build_report(data_root, manifest, write_freeze(manifest.parent, manifest))


def expected(path: Path, data_root: Path, group: str = "tree") -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": "data/" + path.relative_to(data_root).as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "manifest_group": group,
        "role": "relational_object_development",
    }


def test_validator_fails_closed_for_missing_unexpected_and_zero_files(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    placeholder = {"path": "data/expected.conllu", "sha256": "0" * 64, "bytes": 1, "manifest_group": "tree", "role": "relational_object_development"}
    report = report_for(data_root, write_manifest(tmp_path, [placeholder]))
    assert not report["eligible_for_development_forward"]
    assert report["coverage_errors"][0]["code"] == "EXPECTED_PATH_MISSING"

    actual = data_root / "unexpected.conllu"
    actual.write_bytes(doc([ROOT]))
    report = report_for(data_root, write_manifest(tmp_path, [placeholder]))
    assert {item["code"] for item in report["coverage_errors"]} == {"EXPECTED_PATH_MISSING", "UNEXPECTED_PATH"}
    with pytest.raises(ValueError, match="at least one"):
        report_for(data_root, write_manifest(tmp_path, []))


def test_validator_detects_hash_and_duplicate_copy_group(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    a = data_root / "a.conllu"
    b = data_root / "b.conllu"
    a.write_bytes(doc([ROOT], sent_id="same"))
    b.write_bytes(a.read_bytes())
    entries = [expected(a, data_root), expected(b, data_root)]
    report = report_for(data_root, write_manifest(tmp_path, entries))
    assert report["strict_pass_hashes"] == 1  # parse once by hash
    assert report["manifest_errors"][0]["code"] == "SENT_ID_DUPLICATE_MANIFEST"
    assert not report["eligible_for_development_forward"]

    entries[0] = dict(entries[0], sha256="f" * 64)
    report = report_for(data_root, write_manifest(tmp_path, entries))
    assert any(item["code"] == "HASH_MISMATCH" for item in report["coverage_errors"])


def test_validator_verifies_declared_derived_concatenation(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    dev = data_root / "x-dev.conllu"
    test = data_root / "x-test.conllu"
    combo = data_root / "x-devtest.conllu"
    dev.write_bytes(doc([ROOT], sent_id="d"))
    test.write_bytes(doc([ROOT], sent_id="t"))
    combo.write_bytes(dev.read_bytes() + test.read_bytes())
    entries = [expected(dev, data_root, "tree"), expected(test, data_root, "tree"), expected(combo, data_root, "derived")]
    entries[-1]["derived_concatenation_of"] = [entries[0]["path"], entries[1]["path"]]
    manifest = write_manifest(tmp_path, entries)
    assert report_for(data_root, manifest)["eligible_for_development_forward"]
    combo.write_bytes(doc([ROOT], sent_id="other"))
    report = report_for(data_root, manifest)
    assert any(item["code"] == "HASH_MISMATCH" for item in report["coverage_errors"])
    entries[-1] = expected(combo, data_root, "derived")
    entries[-1]["derived_concatenation_of"] = [entries[0]["path"], entries[1]["path"]]
    report = report_for(data_root, write_manifest(tmp_path, entries))
    assert any(item["code"] == "DERIVATION_MISMATCH" for item in report["coverage_errors"])


def test_validator_rejects_manifest_schema_and_identity_drift(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    source = data_root / "a.conllu"
    source.write_bytes(doc([ROOT]))
    manifest = write_manifest(tmp_path, [expected(source, data_root)])
    freeze = write_freeze(tmp_path, manifest)
    report = build_report(data_root, manifest, freeze)
    roles = {item["role"] for item in report["validation_identity"]["inventory"]}
    assert roles == {"plan", "parser", "validator", "tests", "profile_note", "manifest"}

    payload = json.loads(manifest.read_text())
    payload["expected_physical_files"] = 2
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen artifact drift"):
        build_report(data_root, manifest, freeze)

    freeze = write_freeze(tmp_path, manifest)
    with pytest.raises(ValueError, match="expected_physical_files"):
        build_report(data_root, manifest, freeze)


def test_validator_rejects_duplicate_freeze_roles_and_manifest_traversal(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    source = data_root / "a.conllu"
    source.write_bytes(doc([ROOT]))
    manifest = write_manifest(tmp_path, [expected(source, data_root)])
    freeze = write_freeze(tmp_path, manifest)
    frozen = json.loads(freeze.read_text())
    frozen["inventory"].append(dict(frozen["inventory"][0]))
    freeze.write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match="incomplete or duplicated"):
        build_report(data_root, manifest, freeze)

    payload = json.loads(manifest.read_text())
    payload["scan_roots"] = ["data/../outside"]
    payload["entries"][0]["path"] = "data/../outside/a.conllu"
    manifest.write_text(json.dumps(payload))
    freeze = write_freeze(tmp_path, manifest)
    with pytest.raises(ValueError, match="scan_root"):
        build_report(data_root, manifest, freeze)

    payload["scan_roots"] = ["data"]
    payload["entries"][0].pop("role")
    manifest.write_text(json.dumps(payload))
    freeze = write_freeze(tmp_path, manifest)
    with pytest.raises(ValueError, match="malformed opened manifest entry"):
        build_report(data_root, manifest, freeze)
