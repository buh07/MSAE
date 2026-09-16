from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import zipfile

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts/prepare_msae_independent_source_v9.py"
ACQUISITION_SCRIPT = Path(__file__).parents[1] / "scripts/acquire_msae_independent_source_v9.py"
_spec = importlib.util.spec_from_file_location("msae_v9", SCRIPT)
assert _spec and _spec.loader
m = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = m
_spec.loader.exec_module(m)
_acq_spec = importlib.util.spec_from_file_location("msae_v9_acquisition", ACQUISITION_SCRIPT)
assert _acq_spec and _acq_spec.loader
acq = importlib.util.module_from_spec(_acq_spec)
sys.modules[_acq_spec.name] = acq
_acq_spec.loader.exec_module(acq)


def sample_conllu() -> bytes:
    return b"""# sent_id = s1\n# text = A AB Ab a-b ...\n1\tA\ta\tNOUN\t_\tNumber=Sing\t0\troot\t_\t_\n2\tAB\tab\tNOUN\t_\tNumber=Plur\t1\tnmod:poss\t_\t_\n3-4\tAb a-b\t_\t_\t_\t_\t_\t_\t_\t_\n3\tAb\tab\tADJ\t_\t_\t2\tamod\t_\t_\n3.1\tghost\tghost\tX\t_\t_\t_\t_\t_\t_\n4\ta-b\ta-b\tNOUN\t_\t_\t2\tconj\t_\t_\n5\t...\t...\tPUNCT\t_\t_\t3\tpunct\t_\t_\n\n"""


def acquisition_fixture(tmp_path: Path, monkeypatch):
    root=tmp_path;prov=root/"reports/provenance/msae_independent_source_v9";prov.mkdir(parents=True)
    carryover=prov/"v8_carryover_authority.json"
    carryover.write_bytes((SCRIPT.parents[1]/acq.CARRYOVER).read_bytes())
    config=root/"configs/msae_independent_source_v9/acquisition.json";config.parent.mkdir(parents=True)
    config.write_bytes(acq.canonical(acq.expected_config()))
    empty_digest=acq.sha_bytes(acq.canonical_ascii([]))
    registry=prov/"historical_source_registry.json";registry.write_text(json.dumps({
        "schema_version":"msae_independent_source_v9_historical_source_registry_v1",
        "status":"frozen_preacquisition","domain_utf8":"msae-v9/pedigree","inputs":[],
        "input_count":0,"inputs_sha256":empty_digest,"overbound_json_source_key_construct_count":0,
        "quarantine_content_reads":0})+"\n")
    screen=prov/"preacquisition_alias_screen.json";screen.write_text(json.dumps({
        "schema_version":"msae_independent_source_v9_preacquisition_alias_screen_v2",
        "history_input_count":0,"history_inputs_sha256":empty_digest,
        "history_registry_sha256":acq.sha_file(registry),"content_occurrence_count":0,
        "pathname_occurrence_count":0,"source_use_evidence_count":0,"quarantine_content_reads":0,
        "model_operations":0,"gpu_queries":0,"training_runs":0,
        "status":"no_project_source_use_evidence"})+"\n")
    carryover_entry=_acquisition_baseline_entry(root,carryover,"v9_authority")
    baseline=prov/"baseline_inventory.json";baseline.write_bytes(acq.canonical({
        "schema_version":"msae_independent_source_v9_baseline_inventory_v1",
        "training_root_entries":[],"entries":[carryover_entry],"history_inputs_sha256":empty_digest,
        "authority_expected_absent":sorted(acq.V9_AUTHORITY-{acq.CARRYOVER})}))
    authority=prov/"preacquisition_authority_manifest.json"
    authority.write_bytes(acq.canonical({"status":"approved_for_exact_source_acquisition","history_inputs_sha256":empty_digest,"artifact_sha256":{
        "scripts/acquire_msae_independent_source_v9.py":acq.sha_file(ACQUISITION_SCRIPT),
        "configs/msae_independent_source_v9/acquisition.json":acq.sha_file(config),
        acq.CARRYOVER:acq.CARRYOVER_SHA256}}))
    review=root/"reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md";review.parent.mkdir(parents=True)
    review.write_text("VERDICT: SHIP\n"+acq.sha_file(authority)+"\n"+acq.sha_file(baseline))
    monkeypatch.setattr(acq,"ROOT",root);monkeypatch.setattr(acq,"PROV",prov);monkeypatch.setattr(acq,"CONFIG",config)
    monkeypatch.setattr(acq,"BASELINE",baseline);monkeypatch.setattr(acq,"AUTHORITY",authority)
    monkeypatch.setattr(acq,"AUTHORITY_REVIEW",review);monkeypatch.setattr(acq,"ENTRY",prov/"source_acquisition_entry.json")
    monkeypatch.setattr(acq,"REPORT",prov/"source_acquisition.json");monkeypatch.setattr(acq,"REJECTION",prov/"source_acquisition_rejection.json")
    monkeypatch.setattr(acq,"RAW",root/"data/msae_independent_source_v9/raw"/acq.COMMIT)
    monkeypatch.setattr(sys,"argv",[str(ACQUISITION_SCRIPT),"--authority-review-sha256",acq.sha_file(review)])
    return root,prov


def acquisition_success_fixture(tmp_path: Path,monkeypatch):
    _root,_prov=acquisition_fixture(tmp_path,monkeypatch);config=acq.expected_config()
    manifest_sha=acq.sha_file(acq.AUTHORITY);review_sha=acq.sha_file(acq.AUTHORITY_REVIEW);baseline_sha=acq.sha_file(acq.BASELINE)
    entry={"schema_version":"msae_independent_source_v9_source_acquisition_entry_v1","status":"entered",
        "authority_manifest_sha256":manifest_sha,"authority_review_sha256":review_sha,
        "baseline_inventory_sha256":baseline_sha,"config_sha256":acq.sha_file(acq.CONFIG),
        "runner_sha256":acq.sha_file(ACQUISITION_SCRIPT),"source_repo":acq.REPO,"source_commit":acq.COMMIT,
        "files":acq.FILES,"subprocesses_started":0,"model_scoring_authorized":False,
        "k2_or_branch_training_authorized":False,"stage_c_authorized":False}
    acq.ENTRY.write_bytes(acq.canonical(entry));os.chmod(acq.ENTRY,0o644);entry_sha=acq.sha_file(acq.ENTRY)
    raw=acq.RAW;raw.mkdir(parents=True);os.chmod(raw.parent.parent,0o700);os.chmod(raw.parent,0o700)
    files={};blobs={}
    for index,name in enumerate(acq.FILES):
        payload=f"fixture-{index}\n".encode();path=raw/name;path.write_bytes(payload);os.chmod(path,0o444)
        blob=hashlib.sha1(f"blob {len(payload)}\0".encode()+payload,usedforsecurity=False).hexdigest()
        blobs[name]=blob;files[name]={"sha256":acq.sha_bytes(payload),"size":len(payload),"git_blob_sha1":blob,"mode":0o444,"nlink":1}
    os.chmod(raw,0o555);raw_stat=raw.lstat()
    clone_dir="/tmp/msae-v9-acquire-fixture/repo";empty_home="/tmp/msae-v9-acquire-fixture/home"
    argvs=[[*config["ignore_argv"][:-1],"data/msae_independent_source_v9/raw/sentinel"],
           [*config["ignore_argv"][:-1],"data/msae_independent_source_v9/private/sentinel"],
           acq.expand(config["clone_argv"],clone_dir,empty_home),acq.expand(config["checkout_argv"],clone_dir,empty_home),
           acq.expand(config["head_argv"],clone_dir,empty_home),acq.expand(config["tree_argv"],clone_dir,empty_home),
           acq.expand(config["ls_tree_argv"],clone_dir,empty_home),
           *[acq.expand(config["hash_object_argv"],clone_dir,empty_home,name) for name in acq.FILES]]
    names=["ignore_raw","ignore_private","clone","checkout","head","tree","ls_tree",*[
        "hash_object:"+name for name in acq.FILES]]
    tree="b"*40;ls_out=b"".join(f"100644 blob {blobs[name]}\t{name}\0".encode() for name in sorted(acq.FILES))
    outputs=[b"",b"",b"",b"",(acq.COMMIT+"\n").encode(),(tree+"\n").encode(),ls_out,*[
        (blobs[name]+"\n").encode() for name in acq.FILES]]
    commands=[]
    for name,argv,out in zip(names,argvs,outputs):
        commands.append({"name":name,"argv":argv,"exit_status":0,"stdout_bytes":len(out),
            "stdout_sha256":acq.sha_bytes(out),"stderr_bytes":0,"stderr_sha256":acq.sha_bytes(b"")})
    by={item["name"]:item for item in commands}
    report={"schema_version":"msae_independent_source_v9_source_acquisition_v1","source_repo":acq.REPO,
        "source_commit":acq.COMMIT,"resolved_head":acq.COMMIT,"tree_object_sha1":tree,
        "tree_verified_from_ls_tree":True,"tree_paths":acq.FILES,"tree_blob_sha1":blobs,"files":files,
        "authority_manifest_sha256":manifest_sha,"authority_review_sha256":review_sha,
        "source_acquisition_entry_sha256":entry_sha,"acquisition_gate_argument":review_sha,
        "config_sha256":acq.sha_file(acq.CONFIG),"runner_sha256":acq.sha_file(ACQUISITION_SCRIPT),
        "executed_clone_argv":argvs[2],"executed_checkout_argv":argvs[3],
        "environment":{"GIT_CONFIG_NOSYSTEM":"1","GIT_TERMINAL_PROMPT":"0","HOME":empty_home,"PATH":"/usr/bin:/bin"},
        "clone_dir":clone_dir,"empty_home":empty_home,"proxy_variables_present":[],
        "ignore_checks":[{"path":"data/msae_independent_source_v9/raw/sentinel","stdout_sha256":by["ignore_raw"]["stdout_sha256"],
                          "stderr_sha256":by["ignore_raw"]["stderr_sha256"],"exit_status":0},
                         {"path":"data/msae_independent_source_v9/private/sentinel","stdout_sha256":by["ignore_private"]["stdout_sha256"],
                          "stderr_sha256":by["ignore_private"]["stderr_sha256"],"exit_status":0}],
        "commands":commands,"sparse_checkout_sha256":acq.sha_bytes(("\n".join("/"+name for name in acq.FILES)+"\n").encode()),
        "raw_directory":{"device":raw_stat.st_dev,"inode":raw_stat.st_ino,"mode":0o555,"nlink":raw_stat.st_nlink},
        "command_exit_status":{"ignore_raw":0,"ignore_private":0,"clone":0,"checkout":0,"head":0,"tree":0,
                               "ls_tree":0,"hash_object_count":len(acq.FILES)},
        "head_stdout_sha256":by["head"]["stdout_sha256"],"head_stderr_sha256":by["head"]["stderr_sha256"],
        "tree_stdout_sha256":by["tree"]["stdout_sha256"],"tree_stderr_sha256":by["tree"]["stderr_sha256"],
        "ls_tree_stdout_sha256":by["ls_tree"]["stdout_sha256"],"ls_tree_stderr_sha256":by["ls_tree"]["stderr_sha256"],
        "clone_stdout_sha256":by["clone"]["stdout_sha256"],"clone_stderr_sha256":by["clone"]["stderr_sha256"],
        "checkout_stdout_sha256":by["checkout"]["stdout_sha256"],"checkout_stderr_sha256":by["checkout"]["stderr_sha256"],
        "source_content_printed":False,"network_access":"git_clone_and_checkout_only",
        "model_operations":0,"gpu_queries":0,"training_runs":0}
    return report,entry_sha,manifest_sha,review_sha,baseline_sha


def test_parse_and_exact_label_contract(tmp_path: Path):
    path = tmp_path / "x.conllu"
    path.write_bytes(sample_conllu())
    sentences, counts = m.parse_conllu(path)
    assert counts == {"integer_tokens": 5, "multiword_rows": 1, "empty_node_rows": 1}
    s = sentences[0]
    rows = m.sentence_labels(s)
    assert [r["absolute_bucket"] for r in rows] == ["0", "1", "2", "3", "4"]
    assert [r["relative_quartile"] for r in rows] == ["0", "0", "1", "2", "3"]
    assert [r["sentence_boundary"] for r in rows] == ["initial", "interior", "interior", "interior", "final"]
    assert [r["head_signed_distance"] for r in rows] == ["ROOT", "L1_2", "L1_2", "L1_2", "L1_2"]
    assert [r["dependency_depth"] for r in rows] == ["0", "1", "2", "2", "3"]
    assert [r["capitalization"] for r in rows] == ["upper", "upper", "title", "lower", "nonalpha"]
    assert [r["word_length"] for r in rows] == ["1", "2", "2", "3_4", "3_4"]
    assert [r["punctuation"] for r in rows] == ["NONPUNCT"] * 4 + ["PUNCT"]
    assert rows[0]["number"] == "Sing" and rows[1]["number"] == "Plur"
    assert rows[2]["number"] is None and rows[1]["deprel_coarse"] == "nmod"


@pytest.mark.parametrize("feats", ["Number=Sing|Number=Plur", "Number=Sing,Plur", "=x", "A="])
def test_bad_feats_are_terminal(tmp_path: Path, feats: str):
    raw = sample_conllu().replace(b"Number=Sing", feats.encode(), 1)
    path = tmp_path / "bad.conllu"
    path.write_bytes(raw)
    with pytest.raises(m.GateFailure):
        m.parse_conllu(path)


def test_ud_multivalue_nonnumber_is_allowed_and_canonical(tmp_path: Path):
    path = tmp_path / "multi.conllu"
    path.write_bytes(sample_conllu().replace(b"Number=Sing", b"PronType=Int,Rel", 1))
    sentences, _ = m.parse_conllu(path)
    assert m.sentence_labels(sentences[0])[0]["number"] is None


@pytest.mark.parametrize("feats", ["PronType=Rel,Int", "PronType=Int,,Rel", "PronType=Int,Int"])
def test_noncanonical_multivalue_feats_are_terminal(tmp_path: Path, feats: str):
    path = tmp_path / "bad_multi.conllu"
    path.write_bytes(sample_conllu().replace(b"Number=Sing", feats.encode(), 1))
    with pytest.raises(m.GateFailure):
        m.parse_conllu(path)


def test_cycle_is_terminal(tmp_path: Path):
    path = tmp_path / "cycle.conllu"
    path.write_bytes(sample_conllu().replace(b"\t0\troot", b"\t2\troot", 1))
    with pytest.raises(m.GateFailure):
        m.parse_conllu(path)


def test_overlap_rules_and_orientation():
    assert m.overlap_reason(("show", "flights"), ("please", "show", "flights", "now")) == "contained_short"
    a = tuple(f"w{i}" for i in range(24))
    assert m.overlap_reason(a, a) == "exact"
    assert m.overlap_reason(a, a[:-1] + ("other",)) in {"fivegram_jaccard", "covered_fivegrams"}
    assert m.overlap_reason(("...",), ("---",)) is None


def test_split_and_manifest_golden():
    rows = [
        {"sent_id": "x!", "group_id": "doc-a"},
        {"sent_id": "\u00e9", "group_id": "doc-a"},
        {"sent_id": "z", "group_id": "doc-b"},
    ]
    assigned = m.assign_split(rows)
    assert {x["panel"] for x in assigned} == {"C1", "C2"}
    assert len({x["panel"] for x in assigned if x["group_id"] == "doc-a"}) == 1
    assert [x["within_group_rank"] for x in assigned if x["group_id"] == "doc-a"] == [0, 1]
    golden = {
        "schema_version": "msae_independent_source_v9_split_manifest_v1",
        "source_commit": "0" * 40,
        "upstream_partition": "test",
        "test_group_policy": "explicit_newdoc",
        "split_algorithm": "sha256-canonical-json-group-v1-even-C1-odd-C2",
        "pre_dedup_group_count": 2,
        "retained_group_count": 2,
        "fully_removed_group_count": 0,
        "group_count": 2,
        "C1_group_count": 1,
        "C2_group_count": 1,
        "record_count": 3,
        "C1_count": 2,
        "C2_count": 1,
        "entries": [
            {"sent_id": "a", "panel": "C1", "group_rank": 0, "within_group_rank": 0,
             "group_key_sha256": "0" * 64, "group_id_sha256": "1" * 64, "source_record_sha256": "2" * 64},
            {"sent_id": "b", "panel": "C1", "group_rank": 0, "within_group_rank": 1,
             "group_key_sha256": "0" * 64, "group_id_sha256": "1" * 64, "source_record_sha256": "3" * 64},
            {"sent_id": "c", "panel": "C2", "group_rank": 1, "within_group_rank": 0,
             "group_key_sha256": "f" * 64, "group_id_sha256": "e" * 64, "source_record_sha256": "4" * 64},
        ],
    }
    assert hashlib.sha256(m.canonical_file_bytes(golden)).hexdigest() == "aba4c8f6b9fde95fa2e02af7c3d04024c02c23a2d76cea429f413d6f19539db1"
    assert m.group_split_key("doc-a", "0" * 40) == hashlib.sha256(
        m.canonical_bytes(["msae-independent-source-v9/C1C2-group", "0" * 40, "doc-a"])).hexdigest()


def test_create_once_private_payload_and_no_source_output(tmp_path: Path, capsys):
    private = tmp_path / "private"
    records = [{"canary": "MSAE_V9_SECRET_7f6b6aa8", "id": 1}]
    path = m.publish_private_jsonl(private, "payload.jsonl", records)
    assert path.stat().st_mode & 0o777 == 0o600
    assert private.stat().st_mode & 0o777 == 0o700
    assert capsys.readouterr() == ("", "")
    with pytest.raises(m.GateFailure, match="payload_already_exists"):
        m.publish_private_jsonl(private, "payload.jsonl", records)


def test_document_group_marker_and_fallback_are_deterministic(tmp_path: Path):
    path = tmp_path / "grouped.conllu"
    path.write_bytes(b"# newdoc id = DOC-A\n" + sample_conllu())
    sentences, _ = m.parse_conllu(path)
    assert sentences[0].group_id == "doc-a"
    plain = tmp_path / "plain.conllu"; plain.write_bytes(sample_conllu())
    fallback, _ = m.parse_conllu(plain)
    assert fallback[0].group_id == "sent_id_as_group:s1"


def test_document_marker_applies_only_to_following_sentence_without_blank(tmp_path: Path):
    first=sample_conllu().rstrip(b"\n")
    second=sample_conllu().replace(b"# sent_id = s1",b"# sent_id = s2")
    path=tmp_path/"adjacent_marker.conllu"
    path.write_bytes(b"# newdoc id = first\n"+first+b"\n# newdoc id = second\n"+second)
    sentences,_=m.parse_conllu(path)
    assert [(item.sent_id,item.group_id) for item in sentences]==[("s1","first"),("s2","second")]


@pytest.mark.parametrize("prefix", [b"# newdoc id = a\n# newdoc id = b\n", b"# newdoc id = a\n"])
def test_empty_or_trailing_document_group_is_terminal(tmp_path: Path, prefix: bytes):
    path = tmp_path / "bad_group.conllu"
    payload = prefix + (sample_conllu() if prefix.count(b"newdoc") == 2 else b"")
    path.write_bytes(payload)
    with pytest.raises(m.GateFailure, match="empty_document_group"):
        m.parse_conllu(path)


def test_cross_partition_explicit_document_id_is_terminal():
    token = m.Token(1, "x", "x", "NOUN", "_", 0, "root")
    roles = {"discovery":[m.Sentence("a",(token,),0,"same")],
             "calibration":[m.Sentence("b",(token,),0,"same")],
             "test":[m.Sentence("c",(token,),0,"other")]}
    with pytest.raises(m.GateFailure, match="cross_partition_document_id"):
        m.validate_partition_group_ids(roles)


def test_license_evidence_is_boundary_exact():
    good = m.license_evidence("(CC BY-SA 4.0) https://creativecommons.org/licenses/by-sa/4.0/")
    assert good["eligible"] and good["positive_occurrence_count"] == 2
    assert m.license_evidence("HTTPS://CREATIVECOMMONS.ORG/LICENSES/BY-SA/4.0")["eligible"]
    assert m.license_evidence("Attribution ShareAlike 4.0 International")["eligible"]
    for bad in ("https://creativecommons.org/licenses/by-sa/4.01",
                "https://creativecommons.org/licenses/by-sa/4.0evil",
                "https://creativecommons.org/licenses/by-sa/4.0?query=1",
                "https://creativecommons.org/licenses/by-sa/4.0#fragment",
                "prefixhttps://creativecommons.org/licenses/by-sa/4.0",
                "éhttps://creativecommons.org/licenses/by-sa/4.0",
                "https://creativecommons.org/licenses/by-sa/4.0é",
                "xcc by sa 4 0commercial", "CC BY-SA 4.0 but no redistribution"):
        assert not m.license_evidence(bad)["eligible"], bad


def test_v9_license_gate_reads_only_license_txt(tmp_path: Path, monkeypatch):
    raw=tmp_path/"raw";raw.mkdir()
    (raw/"LICENSE.txt").write_text("CC BY-SA 4.0",encoding="utf-8")
    monkeypatch.setattr(m,"RAW",raw)
    value=m._license()
    assert value["status"]=="eligible"
    assert set(value["evidence"])=={"LICENSE.txt"}
    assert "readme_sha256" not in value


def test_dedup_is_prospective_and_removes_all_cross_partition_copies():
    def sentence(sent_id: str, form: str, index: int) -> m.Sentence:
        token = m.Token(1, form, form.casefold(), "NOUN", "_", 0, "root")
        return m.Sentence(sent_id, (token,), index)

    roles = {
        "discovery": [sentence("b", "Same", 0), sentence("a", "same", 1), sentence("only_train", "train", 2)],
        "calibration": [sentence("dev_copy", "SAME", 0), sentence("only_dev", "dev", 1)],
        "test": [sentence("only_test", "test", 0)],
    }
    kept, report = m.deduplicate_roles(roles)
    assert [item.sent_id for item in kept["discovery"]] == ["only_train"]
    assert [item.sent_id for item in kept["calibration"]] == ["only_dev"]
    assert report["roles"]["discovery"]["within_partition_dropped_count"] == 1
    assert report["roles"]["discovery"]["cross_partition_dropped_count"] == 1
    assert report["roles"]["calibration"]["cross_partition_dropped_count"] == 1


def test_fully_removed_test_group_is_omitted_before_group_rank():
    def sentence(sent_id: str, form: str, index: int, group: str) -> m.Sentence:
        token=m.Token(1,form,form.casefold(),"NOUN","_",0,"root")
        return m.Sentence(sent_id,(token,),index,group)
    roles={
        "discovery":[sentence("train","shared",0,"train")],
        "calibration":[sentence("dev","dev",0,"dev")],
        "test":[sentence("removed","SHARED",0,"removed-group"),
                sentence("kept-a","alpha",1,"kept-a-group"),
                sentence("kept-b","beta",2,"kept-b-group")],
    }
    kept,report=m.deduplicate_roles(roles)
    assert report["test_groups"]["pre_dedup_group_count"]==3
    assert report["test_groups"]["retained_group_count"]==2
    assert report["test_groups"]["fully_removed_group_count"]==1
    assigned=m.assign_split([{"sent_id":item.sent_id,"group_id":item.group_id,"sentence":item}
                             for item in kept["test"]])
    assert {item["group_rank"] for item in assigned}=={0,1}
    assert {item["group_id"] for item in assigned}=={"kept-a-group","kept-b-group"}


def test_json_isolated_field_is_scanned_even_when_physical_line_is_long():
    target = "one two three four five six seven eight nine ten"
    row = json.dumps({"text": target, "metadata": " ".join(f"noise{i}" for i in range(100))})
    units = list(m._history_text_units(row + "\n", ".jsonl"))
    assert tuple(target.split()) in units
    assert len(units[-1]) > 10


def test_safe_archive_and_nested_archive_policy(tmp_path: Path):
    import io
    import tarfile
    import zipfile

    safe = tmp_path / "safe.zip"
    with zipfile.ZipFile(safe, "w") as archive:
        archive.writestr("rows.jsonl", '{"text":"ten lexical tokens live only inside this isolated json field now"}\n')
    members = m.archive_members(safe)
    assert members and members[0][0] == "rows.jsonl"
    assert any(unit for unit in m._history_units(safe, "safe_archive_members"))

    nested = tmp_path / "nested.zip"
    with zipfile.ZipFile(nested, "w") as archive:
        archive.writestr("inner.gz", b"\x1f\x8bnot-really-gzip")
    with pytest.raises(m.GateFailure, match="nested_archive"):
        m.archive_members(nested)

    nested_tar = tmp_path / "nested_tar.zip"
    tar_bytes = io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w") as archive:
        info = tarfile.TarInfo("x.txt"); payload = b"x"; info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    with zipfile.ZipFile(nested_tar, "w") as archive:
        archive.writestr("inner.bin", tar_bytes.getvalue())
    with pytest.raises(m.GateFailure, match="nested_archive"):
        m.archive_members(nested_tar)

    wrong_magic = tmp_path / "wrong.zip"
    wrong_magic.write_text("not a zip", encoding="utf-8")
    with pytest.raises(m.GateFailure, match="archive_magic_suffix_mismatch"):
        m.archive_members(wrong_magic)


def test_archive_scan_rejects_symlink_and_path_swap(tmp_path: Path, monkeypatch):
    original=tmp_path/"original.zip";replacement=tmp_path/"replacement.zip"
    with zipfile.ZipFile(original,"w") as archive:archive.writestr("first.txt","first")
    with zipfile.ZipFile(replacement,"w") as archive:archive.writestr("second.txt","second")
    symlink=tmp_path/"symlink.zip";symlink.symlink_to(replacement)
    with pytest.raises(m.GateFailure):m.archive_members(symlink)

    real_kind=m._archive_kind;swapped=False
    def swap_after_bound_probe(payload: bytes) -> str | None:
        nonlocal swapped
        kind=real_kind(payload)
        if not swapped:
            swapped=True;original.unlink();original.symlink_to(replacement)
        return kind
    monkeypatch.setattr(m,"_archive_kind",swap_after_bound_probe)
    with pytest.raises(m.GateFailure,match="archive_path_identity_drift"):
        m.archive_members(original)


def test_pedigree_normalization_git_equivalence_and_hash_domain():
    variants = [
        b"http://github.com/UniversalDependencies/UD_English-ParTUT.git/",
        b"https://github.com/universaldependencies/ud_english-partut.git",
        b"https://github.com/universaldependencies/ud_english-partut/",
    ]
    normalized = {m.normalize_pedigree(value) for value in variants}
    assert normalized == {"https://github.com/universaldependencies/ud_english-partut"}
    value = normalized.pop()
    assert m.pedigree_hash(value) == hashlib.sha256(b"msae-v9/pedigree\0" + value.encode()).hexdigest()


def test_pedigree_json_whitespace_bound_is_exact():
    accepted=b'"dataset"'+b" "*256+b":"+b"\t"*256+b'"UD_Swedish-Talbanken"'
    assert m.PEDIGREE_JSON.search(accepted).group(1)==b"UD_Swedish-Talbanken"
    assert not any(pattern.search(accepted) for pattern in m.PEDIGREE_OVERBOUND)
    for rejected in (b'"dataset"'+b" "*257+b':"x"',
                     b'"dataset"'+b" "*256+b":"+b"\n"*257+b'"x"'):
        assert any(pattern.search(rejected) for pattern in m.PEDIGREE_OVERBOUND)


def test_candidate_pedigree_url_and_ud_limits_are_exact():
    # The URL capture bound applies to the post-scheme URL-character run, not total bytes.
    accepted_url=b"https://"+b"a"*512
    assert m.normalize_pedigree(accepted_url) in m.candidate_pedigree_identifiers(accepted_url+b" ")
    reviewer_regression=b"https://"+b"a"*505
    assert m.normalize_pedigree(reviewer_regression) in m.candidate_pedigree_identifiers(
        reviewer_regression+b" ")
    with pytest.raises(m.GateFailure,match="overlength_candidate_pedigree_identifier"):
        m.candidate_pedigree_identifiers(b"https://"+b"a"*513+b" ")

    accepted_ud=b"UD_"+b"a"*128
    assert m.normalize_pedigree(accepted_ud) in m.candidate_pedigree_identifiers(accepted_ud+b" ")
    with pytest.raises(m.GateFailure,match="overlength_candidate_pedigree_identifier"):
        m.candidate_pedigree_identifiers(b"UD_"+b"a"*129+b" ")


@pytest.mark.parametrize("identifier",(
    b"https://example.invalid/prior-source",
    b"UD_Prior-Treebank",
    b'"dataset"'+b" "*256+b":"+b"\t"*256+b'"UD_Prior-Treebank"',
))
def test_candidate_pedigree_chunk_boundary_emits_complete_match_once(identifier: bytes):
    padding=b" "*(m.PEDIGREE_CHUNK_BYTES-len(identifier)//2)
    expected=(b"UD_Prior-Treebank" if identifier.startswith(b'"dataset"') else identifier)
    values=m.candidate_pedigree_identifiers(padding+identifier+b" ")
    assert values=={m.normalize_pedigree(expected)}


def test_candidate_pedigree_overbound_json_whitespace_crosses_chunk():
    prefix=b'"dataset"'+b" "*257+b':"x"'
    payload=b" "*(m.PEDIGREE_CHUNK_BYTES-200)+prefix
    with pytest.raises(m.GateFailure,match="overbound_candidate_pedigree_whitespace"):
        m.candidate_pedigree_identifiers(payload)


def test_candidate_pedigree_tail_start_preserves_ud_left_context():
    padding=b" "*(m.PEDIGREE_CHUNK_BYTES-m.PEDIGREE_OVERLAP_BYTES-1)
    payload=padding+b"xUD_FalseBoundary "+b" "*(m.PEDIGREE_OVERLAP_BYTES+32)
    assert not m.PEDIGREE_UD.search(payload)
    assert m.candidate_pedigree_identifiers(payload)==set()


def test_registry_history_binding_is_exact():
    records=[{"path":"a.txt","sha256":"a"*64,"size":3}]
    inventory={"entries":[{"path":"a.txt","sha256":"a"*64,"size":3,"disposition":"text_scanned"}]}
    registry={"schema_version":"msae_independent_source_v9_historical_source_registry_v1",
              "status":"frozen_preacquisition","domain_utf8":"msae-v9/pedigree",
              "overbound_json_source_key_construct_count":0,
              "input_count":1,"inputs":records,"inputs_sha256":m.sha_bytes(
                  json.dumps(records,sort_keys=True,ensure_ascii=True,separators=(",",":"),allow_nan=False).encode())}
    screen={"schema_version":"msae_independent_source_v9_preacquisition_alias_screen_v2",
            "history_input_count":1,"history_inputs_sha256":registry["inputs_sha256"],
            "content_occurrence_count":0,"pathname_occurrence_count":0,"source_use_evidence_count":0,
            "status":"no_project_source_use_evidence"}
    m.validate_history_registry_binding(inventory,registry,screen)
    inventory["entries"][0]["size"]=4
    with pytest.raises(m.GateFailure,match="history_registry_input_drift"):
        m.validate_history_registry_binding(inventory,registry,screen)


def test_frozen_v9_plan_chain_matches_reviewed_source_free_artifacts():
    assert m.verify_frozen_v9_authority_bindings()=={
        "docs/plan-msae-independent-source-v9.md":
            "0607886af9561d8418fd7a153322e6b59cd47404f33174c49b07bec5284cd57e",
        "reports/adversarial/msae_independent_source_v9_plan_review.md":
            "5e471cde50c9b4cda8e8f4ad8aca178e235d8a8b9d981a78d9e5b588f96aaee7",
        "reports/provenance/msae_independent_source_v9/v8_carryover_authority.json":
            "00d7cdca4e9893ef1f4e36b6104caf21991ce1ca92e9897d3c5a72d497212f47",
        "reports/provenance/msae_independent_source_v9/historical_source_registry.json":
            "3166d09141374506d7d200fa8d630a66e4a790f5a3f2e81778ed522d4a327863",
        "reports/provenance/msae_independent_source_v9/preacquisition_alias_screen.json":
            "cdda84035279b78698f98c760c5ce12d5276b9b2afbc8e4218133d8207dccafd",
    }


def test_predecessor_chain_includes_and_rehashes_terminal_v7_without_raw_reads():
    expected_v7={
        "docs/plan-msae-independent-source-v7.md":"67053a1b4a222de2fd9de18c534f2f5e58024413224e859c7ddfed4b63261916",
        "reports/adversarial/msae_independent_source_v7_plan_review.md":"3f8ceedbd4be7f3335b8675f1e241e7fd3193719bb4d0bc55a3df54fc19a9429",
        "reports/provenance/msae_independent_source_v7/preacquisition_alias_screen.json":"336a3a4082a1096201ae897715629aff870939d003fc9c6650de748ef16df3d7",
        "reports/provenance/msae_independent_source_v7/historical_source_registry.json":"a5edbe04ce5ca083aa16cc4cade9d64beffe4a0541d67cd7a42dc05e7ec6712f",
        "scripts/prepare_msae_independent_source_v7.py":"ffa487d274699d26035754dac59cc61a01f2383d54872aefe88d633ff25a239c",
        "scripts/acquire_msae_independent_source_v7.py":"2f684b28fe98891df84d7d10c2b11b721f6a7c348f843374eec2a5a858bccd38",
        "tests/test_prepare_msae_independent_source_v7.py":"51bf834e29bc56c743a2dafe981dfa0f85c6d9a4bcc2eb8dbf0be39303dffbea",
        "configs/msae_independent_source_v7/acquisition.json":"30fad65ac10b504a5810b7015c153c53501d18d2dcadc1204795701391b579bd",
        "reports/verification/msae_independent_source_v7_source_free_checks.log":"785a4c4876a567f3b2fc6b167bf5931c81fa64c2df8c0f97492c1ed51d981577",
        "reports/adversarial/msae_independent_source_v7_preacquisition_implementation_review.md":"68cd4493fdccd2d810e14bedc7c6e2c0e8bf28e20f02c1a1195101a17e729884",
        "reports/provenance/msae_independent_source_v7/baseline_inventory.json":"4db1c25dae89a24bed77ceffc9ac315168ddf357b3442e4c467a5cf6aee837b0",
        "reports/provenance/msae_independent_source_v7/preacquisition_authority_manifest.json":"9c049d5bce80fd58e5bd924811f139203de4c133fc944c22a3aace8ee598a5b7",
        "reports/adversarial/msae_independent_source_v7_preacquisition_authority_review.md":"b37513a325bd9ca6b9b65ccdba2a83ce068d63ee14b44b17d99df35334be89a3",
        "reports/provenance/msae_independent_source_v7/source_acquisition_entry.json":"a5ed3430c081704e2b9dd8e7c53e928ebee21841dea3f5dcf7b823632e9fe7fa",
        "reports/provenance/msae_independent_source_v7/source_acquisition_rejection.json":"e71be14d61b76965423f6c209f3049eef156dc1daa5fdccfae80e5c040701a7e",
        "reports/adversarial/msae_independent_source_v7_terminal_failure_review.md":"a9ffad68a78df7b3362ff3900bd7a4e0959a33a63742d29175ba1ccef580207b",
    }
    predecessors=m._predecessor_hashes(hash_raw=False)
    assert len(predecessors)==67
    assert {path:predecessors[path] for path in expected_v7}==expected_v7
    assert all(m.sha_file(SCRIPT.parents[1]/path)==digest for path,digest in predecessors.items())


@pytest.mark.parametrize("owner",("builder","runner"))
def test_descriptor_walker_rejects_ancestor_exchange(tmp_path: Path, monkeypatch, owner: str):
    root=tmp_path/"root";nested=root/"ancestor"/"child";nested.mkdir(parents=True)
    (nested/"frozen.txt").write_text("frozen",encoding="utf-8")
    module=m if owner=="builder" else acq
    monkeypatch.setattr(module,"ROOT",root)
    old_inode=nested.lstat().st_ino;real_listdir=os.listdir;swapped=False
    def exchange(fd):
        nonlocal swapped
        if isinstance(fd,int) and os.fstat(fd).st_ino==old_inode and not swapped:
            swapped=True
            nested.rename(root/"ancestor"/"moved-child")
            nested.mkdir();(nested/"replacement.txt").write_text("replacement",encoding="utf-8")
        return real_listdir(fd)
    monkeypatch.setattr(os,"listdir",exchange)
    failure=m.GateFailure if owner=="builder" else acq.AcquisitionFailure
    walker=(lambda:list(m._walk_paths_allow_v9(include_v9=True))) if owner=="builder" else (
        lambda:list(acq.walk_history_paths()))
    with pytest.raises(failure,match="path_identity_changed"):
        walker()
    assert swapped


def test_partial_raw_metadata_rejects_ancestor_exchange(tmp_path: Path, monkeypatch):
    root=tmp_path/"root";namespace=root/"data/msae_independent_source_v9"
    raw=namespace/"raw";raw.mkdir(parents=True);(raw/"part").write_text("opaque",encoding="utf-8")
    monkeypatch.setattr(acq,"ROOT",root)
    monkeypatch.setattr(acq,"RAW",raw/acq.COMMIT)
    old_inode=raw.lstat().st_ino;real_listdir=os.listdir;swapped=False
    def exchange(fd):
        nonlocal swapped
        if isinstance(fd,int) and os.fstat(fd).st_ino==old_inode and not swapped:
            swapped=True
            raw.rename(namespace/"moved-raw");raw.mkdir();(raw/"replacement").write_text("x")
        return real_listdir(fd)
    monkeypatch.setattr(os,"listdir",exchange)
    with pytest.raises(acq.AcquisitionFailure,match="path_identity_changed"):
        acq.partial_raw_metadata()
    assert swapped


@pytest.mark.parametrize("owner",("builder","runner"))
def test_descriptor_walker_does_not_exclude_v9_prefix_sibling(
        tmp_path: Path, monkeypatch, owner: str):
    root=tmp_path/"root";sibling=root/"data/msae_independent_source_v9_shadow"
    sibling.mkdir(parents=True);(sibling/"late.txt").write_text("late",encoding="utf-8")
    module=m if owner=="builder" else acq
    monkeypatch.setattr(module,"ROOT",root)
    paths=(m._walk_paths() if owner=="builder" else acq.walk_history_paths())
    assert "data/msae_independent_source_v9_shadow/late.txt" in {rel for _path,rel in paths}


def _acquisition_baseline_entry(root: Path, path: Path, disposition: str) -> dict[str, object]:
    st=path.lstat()
    return {"path":path.relative_to(root).as_posix(),"size":st.st_size,
        "mode":st.st_mode&0o777,"device":st.st_dev,"inode":st.st_ino,"nlink":st.st_nlink,
        "mtime_ns":st.st_mtime_ns,"sha256":acq.sha_file(path),"disposition":disposition,
        "adapter":"authority" if disposition=="v9_authority" else "opaque_binary",
        "content_reads":1,"extracted_unit_count":0,"hardlink_aliases":[]}


def test_acquisition_history_binding_rejects_unknown_v9_provenance(tmp_path: Path, monkeypatch):
    _root,prov=acquisition_fixture(tmp_path,monkeypatch)
    (prov/"unreviewed_alias_note.txt").write_text("candidate alias",encoding="utf-8")
    with pytest.raises(acq.AcquisitionFailure,match="history_structural_drift"):
        acq.validate_baseline_history_binding()


@pytest.mark.parametrize("disposition,relative",(
    ("binary_unscanned","cache.pyc"),
    ("v9_authority","docs/plan-msae-independent-source-v9.md"),
))
def test_acquisition_history_binding_hashes_opaque_and_authority_entries(
        tmp_path: Path, monkeypatch, disposition: str, relative: str):
    root,_prov=acquisition_fixture(tmp_path,monkeypatch)
    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b"before-bytes")
    entry=_acquisition_baseline_entry(root,path,disposition)
    baseline=acq.strict_json(acq.BASELINE);baseline["entries"].append(entry)
    baseline["authority_expected_absent"]=[value for value in baseline["authority_expected_absent"]
                                           if value!=relative]
    acq.BASELINE.write_bytes(acq.canonical(baseline))
    before=path.lstat();path.write_bytes(b"after!-bytes")
    assert path.lstat().st_size==before.st_size
    os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
    with pytest.raises(acq.AcquisitionFailure,match="history_snapshot_hash_drift"):
        acq.validate_baseline_history_binding()


def test_acquisition_history_binding_rejects_unknown_disposition(tmp_path: Path, monkeypatch):
    root,_prov=acquisition_fixture(tmp_path,monkeypatch)
    path=root/"history.bin";path.write_bytes(b"fixed")
    entry=_acquisition_baseline_entry(root,path,"binary_unscanned");entry["disposition"]="mystery"
    baseline=acq.strict_json(acq.BASELINE);baseline["entries"]=[entry]
    acq.BASELINE.write_bytes(acq.canonical(baseline))
    with pytest.raises(acq.AcquisitionFailure,match="history_baseline_schema"):
        acq.validate_baseline_history_binding()


def test_acquisition_history_binding_returns_registry_array_digest_and_reaches_entry(
        tmp_path: Path, monkeypatch):
    root,prov=acquisition_fixture(tmp_path,monkeypatch)
    text_path=root/"historical.txt";text_path.write_text("historical text",encoding="utf-8")
    binary_path=root/"historical.bin";binary_path.write_bytes(b"\x00opaque-history")
    text_entry=_acquisition_baseline_entry(root,text_path,"text_scanned")
    text_entry["adapter"]="plain_text";text_entry["extracted_unit_count"]=1
    binary_entry=_acquisition_baseline_entry(root,binary_path,"binary_unscanned")
    records=[{"path":text_entry["path"],"sha256":text_entry["sha256"],"size":text_entry["size"]}]
    history_digest=acq.sha_bytes(acq.canonical_ascii(records))
    registry={"schema_version":"msae_independent_source_v9_historical_source_registry_v1",
        "status":"frozen_preacquisition","domain_utf8":"msae-v9/pedigree","inputs":records,
        "input_count":1,"inputs_sha256":history_digest,"overbound_json_source_key_construct_count":0,
        "quarantine_content_reads":0}
    (prov/"historical_source_registry.json").write_text(json.dumps(registry)+"\n",encoding="utf-8")
    screen={"schema_version":"msae_independent_source_v9_preacquisition_alias_screen_v2",
        "history_input_count":1,"history_inputs_sha256":history_digest,
        "history_registry_sha256":acq.sha_file(prov/"historical_source_registry.json"),
        "content_occurrence_count":0,"pathname_occurrence_count":0,"source_use_evidence_count":0,
        "quarantine_content_reads":0,"model_operations":0,"gpu_queries":0,"training_runs":0,
        "status":"no_project_source_use_evidence"}
    (prov/"preacquisition_alias_screen.json").write_text(json.dumps(screen)+"\n",encoding="utf-8")
    baseline=acq.strict_json(acq.BASELINE)
    baseline.update(entries=[*baseline["entries"],text_entry,binary_entry],history_inputs_sha256=history_digest)
    acq.BASELINE.write_bytes(acq.canonical(baseline))
    authority=acq.strict_json(acq.AUTHORITY);authority["history_inputs_sha256"]=history_digest
    acq.AUTHORITY.write_bytes(acq.canonical(authority))
    acq.AUTHORITY_REVIEW.write_text(
        "VERDICT: SHIP\n"+acq.sha_file(acq.AUTHORITY)+"\n"+acq.sha_file(acq.BASELINE),encoding="utf-8")
    monkeypatch.setattr(sys,"argv",[str(ACQUISITION_SCRIPT),"--authority-review-sha256",
                                    acq.sha_file(acq.AUTHORITY_REVIEW)])
    assert acq.validate_baseline_history_binding()==history_digest
    calls=[]
    def stop_at_first_process(argv,**_kwargs):
        calls.append(argv)
        assert acq.ENTRY.is_file()
        return acq.subprocess.CompletedProcess(argv,1,b"",b"fixture")
    monkeypatch.setattr(acq.subprocess,"run",stop_at_first_process)
    with pytest.raises(acq.AcquisitionFailure,match="command_failed"):acq.entrypoint()
    assert len(calls)==1


def test_source_family_alias_scan_catches_chunk_boundary(tmp_path: Path, monkeypatch):
    path=tmp_path/"history.txt"
    path.write_bytes(b" "*(1024*1024-3)+b"swe"+b"dish talbanken ")
    monkeypatch.setattr(m,"ROOT",tmp_path)
    monkeypatch.setattr(m,"validate_history_registry_binding",lambda _inventory:"a"*64)
    inventory={"entries":[{"path":"history.txt","sha256":m.sha_file(path),
                           "disposition":"text_scanned"}]}
    result=m._source_family(inventory,set())
    assert result["status"]=="ineligible"
    assert result["content_occurrence_count"]==1
    assert result["content_occurrences"]==[{"path":"history.txt","aliases":["swedish talbanken"]}]


def test_source_family_scan_rejects_mutation_during_read(tmp_path: Path, monkeypatch):
    path=tmp_path/"history.txt";path.write_bytes(b"ordinary history")
    before=path.lstat();monkeypatch.setattr(m,"ROOT",tmp_path)
    monkeypatch.setattr(m,"validate_history_registry_binding",lambda _inventory:"a"*64)
    inventory={"entries":[{"path":"history.txt","sha256":m.sha_file(path),
                           "disposition":"text_scanned"}]}
    real_read=os.read;changed=False
    def mutate_after_read(fd: int, amount: int) -> bytes:
        nonlocal changed
        payload=real_read(fd,amount)
        if payload and not changed:
            changed=True;path.write_bytes(b"mutated history")
            os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
        return payload
    monkeypatch.setattr(os,"read",mutate_after_read)
    with pytest.raises(m.GateFailure,match="file_mutated_while_reading"):
        m._source_family(inventory,set())


@pytest.mark.parametrize(
    "source,expected",
    [
        ("import socket\n", "forbidden_import:socket"),
        ("import subprocess\n", "forbidden_import:subprocess"),
        ("import ctypes\n", "forbidden_import:ctypes"),
        ("eval('1')\n", "dynamic_call:eval"),
        ("import os\nos.posix_spawn('/x', ['/x'], {})\n", "forbidden_os_call:posix_spawn"),
        ("from os import system\nsystem('x')\n", "forbidden_os_import:system"),
        ("import os\ngetattr(os, 'execv')('/x', ['/x'])\n", "indirect_forbidden_os_call:execv"),
        ("import os as disguised\ndisguised.system('x')\n", "aliased_os_import"),
        ("from os import *\nsystem('x')\n", "forbidden_os_import:*"),
    ],
)
def test_static_contract_negative_fixtures(tmp_path: Path, source: str, expected: str):
    path = tmp_path / "bad.py"
    path.write_text(source, encoding="utf-8")
    assert expected in m.validate_static_contract(path)


def test_process_snapshot_schema_and_hash_only():
    snapshot = m.process_snapshot()
    assert snapshot["schema_version"] == "msae_independent_source_v9_process_snapshot_v1"
    for item in snapshot["entries"]:
        assert set(item) == {"pid", "start_ticks", "executable_basename", "command_sha256", "forbidden_codes"}
        assert len(item["command_sha256"]) == 64


def test_strict_structured_history_and_census():
    with pytest.raises(m.GateFailure, match="invalid_jsonl_root"):
        list(m._history_text_units('["not", "an", "object"]\n', ".jsonl"))
    with pytest.raises(m.GateFailure, match="invalid_json_root"):
        list(m._history_text_units('{"metadata":"unsupported root"}\n', ".json"))
    census = {}
    units = list(m._history_text_units('{"text":"one two three"}\n{"metadata":1}\n', ".jsonl", census))
    assert ("one", "two", "three") in units
    assert census["structured_rows"] == census["included_rows"] + census["named_nontext_rows"] == 2


def test_history_overlap_detects_reverse_short_containment(tmp_path: Path, monkeypatch):
    history = tmp_path / "history.txt"
    history.write_text("four five six\n", encoding="utf-8")
    st = history.stat()
    inventory = {"entries":[{"path":"history.txt","disposition":"text_scanned","adapter":"physical_lines",
                              "size":st.st_size,"inode":st.st_ino,"mtime_ns":st.st_mtime_ns}]}
    rows = {"discovery":[{"sent_id":"candidate","normalized":"one two three four five six seven eight nine ten"}],
            "calibration":[],"C1":[],"C2":[]}
    monkeypatch.setattr(m,"ROOT",tmp_path)
    hits,_,_ = m._history_overlap(rows,inventory)
    assert hits and hits[0]["reason"] == "contained_short"


def test_inventory_rejects_populated_v9_and_directory_symlink_without_opening(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m,"ROOT",tmp_path)
    raw = tmp_path / "data/msae_independent_source_v9/raw"
    raw.mkdir(parents=True); secret = raw / "secret"; secret.write_text("must not open")
    with pytest.raises(m.GateFailure, match="preexisting_v9_namespace"):
        m.inventory_repository()
    secret.unlink(); raw.rmdir(); (tmp_path/"data/msae_independent_source_v9").rmdir()
    target=tmp_path/"target";target.mkdir();(tmp_path/"linked").symlink_to(target,target_is_directory=True)
    with pytest.raises(m.GateFailure, match="special_paths"):
        m.inventory_repository()


def test_payload_rejects_symlink_directory_and_abandoned_temp(tmp_path: Path):
    target=tmp_path/"real";target.mkdir();linked=tmp_path/"linked";linked.symlink_to(target,target_is_directory=True)
    with pytest.raises(m.GateFailure, match="unsafe_payload_directory"):
        m.publish_private_jsonl(linked,"payload.jsonl",[])
    private=tmp_path/"private";private.mkdir();(private/".payload.jsonl.building").write_text("abandoned")
    with pytest.raises(m.GateFailure, match="abandoned_payload_temporary"):
        m.publish_private_jsonl(private,"payload.jsonl",[])


def test_frozen_acquisition_config():
    config=SCRIPT.parents[1]/"configs/msae_independent_source_v9/acquisition.json"
    value=m.validate_acquisition_config(config)
    assert value["required_runtime_input"] == "authority_review_sha256"


def test_v9_acquisition_count_is_exactly_the_four_frozen_files():
    names=[*m.SOURCE_FILES.values(),"LICENSE.txt"]
    assert len(names)==4
    base={"ignore_raw":0,"ignore_private":0,"clone":0,"checkout":0,"head":0,"tree":0,
          "ls_tree":0,"hash_object_count":4}
    m.validate_acquisition_exit_statuses(base,names)
    for bad in (3,5):
        with pytest.raises(m.GateFailure,match="source_acquisition_exit_status"):
            m.validate_acquisition_exit_statuses({**base,"hash_object_count":bad},names)


def test_real_v8_carryover_authority_has_exact_control_and_opaque_raw_universes():
    value=m.verify_v8_carryover(hash_raw=False)
    assert len(value["v8_control_files"])==17
    assert {item["path"] for item in value["v8_control_files"]}==m.V8_CONTROL_PATHS
    assert len(value["v8_data_directories"])==3
    assert len(value["v8_raw_files"])==4


def test_v9_raw_open_requires_durable_scientific_entry(tmp_path: Path,monkeypatch):
    raw=tmp_path/"raw";raw.mkdir();path=raw/"opaque";path.write_bytes(b"opaque")
    prov=tmp_path/"prov";prov.mkdir()
    monkeypatch.setattr(m,"REAL_V9_RAW",raw);monkeypatch.setattr(m,"PROV",prov)
    monkeypatch.setattr(m,"RAW_FILE_OPEN_COUNT",0);monkeypatch.setattr(m,"RAW_ACCESS_AUTHORIZED",False)
    with pytest.raises(m.GateFailure,match="v9_raw_open_before_scientific_entry"):
        m.read_bytes_nofollow(path)
    m.write_json(prov/"scientific_preparation_entry.json",{"status":"fixture"})
    monkeypatch.setattr(m,"RAW_ACCESS_AUTHORIZED",True)
    assert m.read_bytes_nofollow(path)==b"opaque"
    assert m.RAW_FILE_OPEN_COUNT==1


def test_post_baseline_inventory_is_exact_and_preentry_raw_hashes_are_deferred(
        tmp_path: Path,monkeypatch):
    prov=tmp_path/"reports/provenance/msae_independent_source_v9";prov.mkdir(parents=True)
    raw=tmp_path/"data/msae_independent_source_v9/raw"/m.COMMIT;raw.mkdir(parents=True)
    os.chmod(raw.parent.parent,0o700);os.chmod(raw.parent,0o700)
    monkeypatch.setattr(m,"ROOT",tmp_path);monkeypatch.setattr(m,"PROV",prov)
    monkeypatch.setattr(m,"RAW",raw);monkeypatch.setattr(m,"REAL_V9_RAW",raw)
    monkeypatch.setattr(m,"PRIVATE",tmp_path/"data/msae_independent_source_v9/private")
    common=("baseline_inventory.json","preacquisition_authority_manifest.json",
            "source_acquisition_entry.json")
    for name in common:m.write_json(prov/name,{"name":name})
    review=tmp_path/"reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md"
    review.parent.mkdir(parents=True);review.write_text("review",encoding="utf-8");os.chmod(review,0o644)
    files={}
    for index,name in enumerate(sorted((*m.SOURCE_FILES.values(),"LICENSE.txt"))):
        payload=f"opaque-{index}".encode();path=raw/name
        path.write_bytes(payload);os.chmod(path,0o444)
        files[name]={"sha256":m.sha_bytes(payload),"size":len(payload),
                     "git_blob_sha1":"a"*40,"mode":0o444,"nlink":1}
    os.chmod(raw,0o555)
    m.write_json(prov/"source_acquisition.json",{"files":files})
    baseline={"entries":[]};monkeypatch.setattr(m,"RAW_FILE_OPEN_COUNT",0)
    entry_rel="reports/provenance/msae_independent_source_v9/scientific_preparation_entry.json"
    inventory=m._post_baseline_inventory(baseline,"scientific_entry",entry_rel)
    raw_records=[item for item in inventory["entries"] if item["path"].startswith(
        f"data/msae_independent_source_v9/raw/{m.COMMIT}/")]
    assert len(raw_records)==4
    assert {item["sha256_verification_status"] for item in raw_records}=={"deferred_until_post_entry"}
    assert all(item["content_read"] is False for item in raw_records)
    assert m.RAW_FILE_OPEN_COUNT==0
    m.write_json(prov/"scientific_preparation_entry.json",{"fixture":True})
    rejection_rel="reports/provenance/msae_independent_source_v9/rejection.json"
    b1=m._post_baseline_inventory(baseline,"B1",rejection_rel,verify_raw_hashes=False)
    assert {item["sha256_verification_status"] for item in b1["entries"]
            if item["path"].startswith(f"data/msae_independent_source_v9/raw/{m.COMMIT}/")}=={
                "verified_post_entry"}
    m.write_json(prov/"support.json",{"out_of_order":True})
    with pytest.raises(m.GateFailure,match="scientific_prefix_drift"):
        m._post_baseline_inventory(baseline,"B1",rejection_rel,verify_raw_hashes=False)


def test_inherited_scientific_functions_match_v8_normalized_ast():
    v8=ast.parse((SCRIPT.parents[1]/"scripts/prepare_msae_independent_source_v8.py").read_text())
    v9=ast.parse(SCRIPT.read_text())
    inherited=("parse_feats canonical_group_id _finish_sentence parse_conllu sentence_labels "
        "normalized_sentence lexical_tokens fivegrams overlap_reason assign_split build_split_manifest "
        "payload_record _history_text_units _history_units deduplicate_roles _role_overlap "
        "_history_overlap _support license_evidence _license _group_census_one document_group_census "
        "_source_family normalize_pedigree candidate_pedigree_identifiers candidate_pedigree").split()
    functions=lambda tree:{node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    class Normalize(ast.NodeTransformer):
        def visit_Constant(self,node):
            if isinstance(node.value,str):node.value=node.value.replace("v9","v8").replace("V9","V8")
            return node
    left,right=functions(v8),functions(v9)
    for name in inherited:
        old=Normalize().visit(ast.parse(ast.unparse(left[name]))).body[0]
        new=Normalize().visit(ast.parse(ast.unparse(right[name]))).body[0]
        assert ast.dump(new,include_attributes=False)==ast.dump(old,include_attributes=False),name


def test_training_root_delta_is_terminal(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m,"ROOT",tmp_path)
    result=tmp_path/"results";result.mkdir();existing=result/"old.txt";existing.write_text("old")
    st=existing.stat()
    baseline={"training_root_entries":[{"path":"results/old.txt","size":st.st_size,"mode":st.st_mode & 0o777,
              "inode":st.st_ino,"mtime_ns":st.st_mtime_ns,"sha256":m.sha_file(existing),"disposition":"text_scanned"}]}
    m.verify_training_roots(baseline)
    (result/"new.txt").write_text("new")
    with pytest.raises(m.GateFailure, match="training_root_delta"):
        m.verify_training_roots(baseline)


def test_dynamic_recensuses_report_complete_drift_evidence(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m,"ROOT",tmp_path)
    history=tmp_path/"history.txt";history.write_text("frozen history",encoding="utf-8")
    st=history.lstat()
    entry={"path":"history.txt","disposition":"text_scanned","size":st.st_size,
           "device":st.st_dev,"inode":st.st_ino,"mode":st.st_mode&0o777,"nlink":st.st_nlink,
           "mtime_ns":st.st_mtime_ns,"sha256":m.sha_file(history)}
    expected_inputs=m.sha_bytes(m._canonical_ascii_bytes([
        {"path":"history.txt","sha256":entry["sha256"],"size":entry["size"]}]))
    baseline={"entries":[entry],"entries_sha256":m.sha_bytes(m.canonical_bytes([entry])),
              "history_inputs_sha256":expected_inputs,"training_root_entries":[],
              "training_root_entries_sha256":m.sha_bytes(m.canonical_bytes([]))}

    eligible=m._history_recensus(baseline,set())
    assert eligible["status"]=="eligible"
    assert eligible["observed_entries_sha256"]==baseline["entries_sha256"]
    assert eligible["observed_history_inputs_sha256"]==expected_inputs

    history.write_text("drifted history",encoding="utf-8")
    (tmp_path/"late.txt").write_text("late",encoding="utf-8")
    drift=m._history_recensus(baseline,set())
    assert drift["status"]=="drift" and drift["failure_code"]=="history_recensus_drift"
    assert drift["added_paths"]==["late.txt"] and drift["changed_paths"]==["history.txt"]
    assert drift["removed_paths"]==[]
    assert m._is_sha(drift["observed_entries_sha256"])
    assert m._is_sha(drift["observed_history_inputs_sha256"])
    assert drift["observed_entries_sha256"]!=baseline["entries_sha256"]
    assert drift["observed_history_inputs_sha256"]!=expected_inputs

    history.unlink()
    removed=m._history_recensus(baseline,{"late.txt"})
    assert removed["status"]=="drift" and removed["removed_paths"]==["history.txt"]
    assert removed["added_paths"]==[] and m._is_sha(removed["observed_entries_sha256"])

    results=tmp_path/"results";results.mkdir();(results/"new.txt").write_text("new",encoding="utf-8")
    training=m._training_recensus(baseline)
    assert training["status"]=="drift" and training["failure_code"]=="training_recensus_drift"
    assert training["observed_entry_count"]==1 and m._is_sha(training["observed_entries_sha256"])


def test_preflight_rejection_persists_exact_dynamic_evidence(tmp_path: Path, monkeypatch):
    prov,_private,baseline,_acquisition,snapshot=scientific_terminal_fixture(tmp_path,monkeypatch)
    history=m._failed_history_recensus(baseline,"history_boundary")
    training=m._eligible_training_recensus(baseline)
    m.retain_preflight_rejection("history_boundary",history,training,snapshot)
    value=m.strict_json(prov/"preflight_rejection.json")
    assert value["history_recensus"]==history
    assert value["training_recensus"]==training
    assert value["pre_entry_process_snapshot"]==snapshot
    monkeypatch.setattr(m,"_history_recensus",lambda *_a,**_k:history)
    monkeypatch.setattr(m,"_training_recensus",lambda *_a,**_k:training)
    monkeypatch.setattr(m,"_verify_history_snapshot",
        lambda *_a,**_k:(_ for _ in ()).throw(m.GateFailure("old_boolean_verifier_used")))
    monkeypatch.setattr(m,"verify_training_roots",
        lambda *_a,**_k:(_ for _ in ()).throw(m.GateFailure("old_boolean_verifier_used")))
    m.verify_terminal()


def test_training_root_reconstruction_uses_global_path_order(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m,"ROOT",tmp_path)
    result=tmp_path/"results";result.mkdir()
    a=result/"a.txt";z=result/"z.txt";a.write_text("a");z.write_text("z")
    def record(path: Path, rel: str):
        st=path.stat()
        return {"path":rel,"size":st.st_size,"mode":st.st_mode & 0o777,"inode":st.st_ino,
                "mtime_ns":st.st_mtime_ns,"sha256":m.sha_file(path),"disposition":"text_scanned"}
    expected=[record(a,"results/a.txt"),record(z,"results/z.txt")]
    monkeypatch.setattr(m,"_walk_paths_allow_v9",lambda:iter([(z,"results/z.txt"),(a,"results/a.txt")]))
    m.verify_training_roots({"training_root_entries":expected})

    baseline=tmp_path/"baseline.json";baseline.write_bytes(acq.canonical({"training_root_entries":expected}))
    monkeypatch.setattr(acq,"BASELINE",baseline)
    monkeypatch.setattr(acq,"walk_history_paths",lambda:iter([(z,"results/z.txt"),(a,"results/a.txt")]))
    assert acq.training_root_status()=="unchanged"


def test_authority_manifest_is_create_once_and_review_bound(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m,"ROOT",tmp_path)
    prov=tmp_path/"reports/provenance/msae_independent_source_v9";prov.mkdir(parents=True)
    monkeypatch.setattr(m,"PROV",prov)
    required=[
        "docs/plan-msae-independent-source-v9.md",
        "reports/adversarial/msae_independent_source_v9_plan_review.md",
        "reports/provenance/msae_independent_source_v9/preacquisition_alias_screen.json",
        "reports/provenance/msae_independent_source_v9/historical_source_registry.json",
        "scripts/prepare_msae_independent_source_v9.py",
        "scripts/acquire_msae_independent_source_v9.py",
        "tests/test_prepare_msae_independent_source_v9.py",
        "configs/msae_independent_source_v9/acquisition.json",
        "reports/verification/msae_independent_source_v9_source_free_checks.log",
        m.CARRYOVER_PATH,
    ]
    for rel in required:
        path=tmp_path/rel;path.parent.mkdir(parents=True,exist_ok=True)
        if rel == m.CARRYOVER_PATH:
            path.write_bytes((SCRIPT.parents[1]/rel).read_bytes())
        else:
            path.write_text(rel)
    monkeypatch.setattr(m,"_predecessor_hashes",lambda:{})
    empty_history_sha=m.sha_bytes(m._canonical_ascii_bytes([]))
    registry_path=prov/"historical_source_registry.json"
    registry_path.write_text(json.dumps({
        "schema_version":"msae_independent_source_v9_historical_source_registry_v1",
        "status":"frozen_preacquisition","domain_utf8":"msae-v9/pedigree","inputs":[],
        "input_count":0,"inputs_sha256":empty_history_sha,
        "overbound_json_source_key_construct_count":0})+"\n")
    (prov/"preacquisition_alias_screen.json").write_text(json.dumps({
        "schema_version":"msae_independent_source_v9_preacquisition_alias_screen_v2",
        "history_input_count":0,"history_inputs_sha256":empty_history_sha,
        "history_registry_sha256":m.sha_file(registry_path),"content_occurrence_count":0,
        "pathname_occurrence_count":0,"source_use_evidence_count":0,
        "status":"no_project_source_use_evidence"})+"\n")
    hashes={rel:m.sha_file(tmp_path/rel) for rel in required}
    impl=tmp_path/"reports/adversarial/msae_independent_source_v9_preacquisition_implementation_review.md"
    impl.write_text("VERDICT: SHIP\n"+"\n".join([*hashes.values(),m.sha_file(SCRIPT)]))
    entries=[]
    for path in sorted(item for item in tmp_path.rglob("*") if item.is_file()):
        st=path.lstat();rel=path.relative_to(tmp_path).as_posix()
        entries.append({"path":rel,"disposition":"v9_authority","size":st.st_size,"mode":st.st_mode&0o777,
                        "device":st.st_dev,"inode":st.st_ino,"nlink":st.st_nlink,"mtime_ns":st.st_mtime_ns,
                        "sha256":m.sha_file(path)})
    baseline={"entries":entries,"entries_sha256":m.sha_bytes(m.canonical_bytes(entries)),"training_root_entries":[],
                  "training_root_entries_sha256":m.sha_bytes(m.canonical_bytes([])),"quarantine_content_reads":0,
                  "history_inputs_sha256":empty_history_sha,
                  "process_snapshot":{"status":"eligible","forbidden_identity_count":0}}
    m.write_json(prov/"baseline_inventory.json",baseline)
    m.build_authority_manifest()
    with pytest.raises(m.GateFailure,match="authority_manifest_already_exists"):
        m.build_authority_manifest()
    review=tmp_path/"reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md"
    review.write_text("VERDICT: SHIP\n"+m.sha_file(prov/"preacquisition_authority_manifest.json")+"\n"+m.sha_file(prov/"baseline_inventory.json"))
    chain=m.verify_authority_chain()
    assert chain["status"] == "approved_for_exact_source_acquisition"


def test_atomic_json_handles_short_writes(tmp_path: Path, monkeypatch):
    real_write=os.write
    def short_write(fd: int, data: bytes) -> int:
        return real_write(fd,data[:max(1,min(2,len(data)))])
    monkeypatch.setattr(os,"write",short_write)
    path=tmp_path/"artifact.json";value={"complete":"yes","items":list(range(20))}
    m.write_json(path,value)
    assert json.loads(path.read_text()) == value


def test_baseline_requires_ship_review_before_publication(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m,"ROOT",tmp_path);prov=tmp_path/"reports/provenance/msae_independent_source_v9";prov.mkdir(parents=True)
    monkeypatch.setattr(m,"PROV",prov)
    paths=["docs/plan-msae-independent-source-v9.md","reports/adversarial/msae_independent_source_v9_plan_review.md",
           "reports/provenance/msae_independent_source_v9/preacquisition_alias_screen.json",
           "reports/provenance/msae_independent_source_v9/historical_source_registry.json","tests/test_prepare_msae_independent_source_v9.py",
           "configs/msae_independent_source_v9/acquisition.json","reports/verification/msae_independent_source_v9_source_free_checks.log",
           "scripts/acquire_msae_independent_source_v9.py",m.CARRYOVER_PATH]
    for rel in paths:
        path=tmp_path/rel;path.parent.mkdir(parents=True,exist_ok=True)
        if rel == m.CARRYOVER_PATH:
            path.write_bytes((SCRIPT.parents[1]/rel).read_bytes())
        else:
            path.write_text(rel)
    review=tmp_path/"reports/adversarial/msae_independent_source_v9_preacquisition_implementation_review.md"
    review.write_text("VERDICT: BLOCK\n")
    monkeypatch.setattr(m,"validate_acquisition_config",lambda _path:{})
    with pytest.raises(m.GateFailure,match="review_binding_ineligible"):
        m.build_baseline()
    assert not (prov/"baseline_inventory.json").exists()


def test_overlength_candidate_pedigree_field_is_terminal(tmp_path: Path, monkeypatch):
    raw=tmp_path/"raw";raw.mkdir()
    for name in (*m.SOURCE_FILES.values(),"LICENSE.txt"):
        (raw/name).write_bytes(b"")
    (raw/m.SOURCE_FILES["train"]).write_bytes(b'{"dataset":"'+b"x"*1025+b'"}')
    prov=tmp_path/"prov";prov.mkdir();m.write_json(prov/"historical_source_registry.json",{"entries":[],"allowed_framework_identifiers":[]})
    monkeypatch.setattr(m,"RAW",raw);monkeypatch.setattr(m,"PROV",prov)
    with pytest.raises(m.GateFailure,match="ambiguous_candidate_pedigree_syntax"):
        m.candidate_pedigree()


@pytest.mark.parametrize("partition",("train","dev","test"))
@pytest.mark.parametrize("identifier",("https://example.invalid/prior-source","UD_Prior-Treebank"))
def test_candidate_pedigree_scans_every_conllu_partition_before_later_gates(
        tmp_path: Path, monkeypatch, partition: str, identifier: str):
    raw=tmp_path/"raw";raw.mkdir()
    for name in (*m.SOURCE_FILES.values(),"LICENSE.txt"):
        (raw/name).write_bytes(b"")
    (raw/m.SOURCE_FILES[partition]).write_text(f"# source = {identifier}\n",encoding="utf-8")
    normalized=m.normalize_pedigree(identifier.encode("utf-8"));identifier_hash=m.pedigree_hash(normalized)
    prov=tmp_path/"prov";prov.mkdir()
    m.write_json(prov/"historical_source_registry.json",{
        "entries":[{"identifier_sha256":identifier_hash}],"allowed_framework_identifiers":[]})
    monkeypatch.setattr(m,"RAW",raw);monkeypatch.setattr(m,"PROV",prov)
    result=m.candidate_pedigree()
    assert result["status"]=="ineligible" and result["blocking_identifier_sha256"]==[identifier_hash]
    assert result["candidate_file_identifier_counts"][m.SOURCE_FILES[partition]]==1
    assert result["candidate_file_identifier_sha256"][m.SOURCE_FILES[partition]]==[identifier_hash]


def test_candidate_pedigree_gate_precedes_dedup_support_and_payload():
    source=Path(m.__file__).read_text(encoding="utf-8")
    body=source[source.index("def build_ready() -> None:"):source.index("\ndef retain_rejection",source.index("def build_ready() -> None:"))]
    pedigree=body.index("pedigree=candidate_pedigree()")
    assert pedigree<body.index("deduplicate_roles(")
    assert pedigree<body.index("_support(rows)")
    assert pedigree<body.index("publish_private_jsonl(")


def test_acquisition_report_atomic_short_writes(tmp_path: Path, monkeypatch):
    real_write=os.write
    monkeypatch.setattr(os,"write",lambda fd,data:real_write(fd,data[:max(1,min(3,len(data)))]))
    path=tmp_path/"acquisition.json";value={"complete":True,"items":list(range(15))}
    acq.atomic_json(path,value)
    assert json.loads(path.read_text()) == value


@pytest.mark.parametrize("publisher,error_type",((m.write_json,m.GateFailure),(acq.atomic_json,acq.AcquisitionFailure)))
def test_public_publisher_never_unlinks_replaced_temporary(tmp_path: Path, monkeypatch, publisher, error_type):
    path=tmp_path/"artifact.json";temp=tmp_path/".artifact.json.building";real_write=os.write
    def replace_then_fail(fd: int, _data: bytes) -> int:
        os.unlink(temp)
        temp.write_text("external inode",encoding="utf-8")
        raise OSError("write failure after replacement")
    monkeypatch.setattr(os,"write",replace_then_fail)
    with pytest.raises(error_type,match="temporary_identity_changed"):
        publisher(path,{"fixture":True})
    assert temp.read_text(encoding="utf-8")=="external inode" and not path.exists()
    monkeypatch.setattr(os,"write",real_write)


def test_private_publisher_never_unlinks_replaced_temporary(tmp_path: Path, monkeypatch):
    private=tmp_path/"private";temp=private/".payload.jsonl.building"
    def replace_then_fail(fd: int, _data: bytes) -> int:
        os.unlink(temp);temp.write_text("external private inode",encoding="utf-8")
        raise OSError("private write failure after replacement")
    monkeypatch.setattr(os,"write",replace_then_fail)
    with pytest.raises(m.GateFailure,match="temporary_identity_changed"):
        m.publish_private_jsonl(private,"payload.jsonl",[{"x":1}])
    assert temp.read_text(encoding="utf-8")=="external private inode" and not (private/"payload.jsonl").exists()


@pytest.mark.parametrize("publisher",(m.write_json,acq.atomic_json))
@pytest.mark.parametrize("fault,expected",(
    ("create","absent"),("write","absent"),("file_fsync","absent"),("link","absent"),
    ("unlink","blocked"),("final_check","recoverable_final"),("parent_fsync","recoverable_final")))
def test_atomic_publish_faults_are_absent_or_explicitly_blocked(tmp_path: Path, monkeypatch, publisher, fault: str, expected: str):
    path=tmp_path/"artifact.json";temp=tmp_path/".artifact.json.building"
    real_open,real_write,real_fsync=os.open,os.write,os.fsync
    real_link,real_unlink,real_stat=os.link,os.unlink,os.stat
    calls={"fsync":0}
    if fault=="create":
        monkeypatch.setattr(os,"open",lambda name,flags,*a,**k: (_ for _ in ()).throw(OSError("create"))
            if name==temp.name and flags & os.O_CREAT else real_open(name,flags,*a,**k))
    elif fault=="write":monkeypatch.setattr(os,"write",lambda _fd,_data:(_ for _ in ()).throw(OSError("write")))
    elif fault in {"file_fsync","parent_fsync"}:
        target=1 if fault=="file_fsync" else 3
        def fail_fsync(fd):
            calls["fsync"]+=1
            if calls["fsync"]==target:raise OSError(fault)
            return real_fsync(fd)
        monkeypatch.setattr(os,"fsync",fail_fsync)
    elif fault=="link":monkeypatch.setattr(os,"link",lambda *_a,**_k:(_ for _ in ()).throw(OSError("link")))
    elif fault=="unlink":monkeypatch.setattr(os,"unlink",lambda name,*a,**k:(_ for _ in ()).throw(OSError("unlink"))
        if name==temp.name else real_unlink(name,*a,**k))
    elif fault=="final_check":
        def fail_final(name,*a,**k):
            result=real_stat(name,*a,**k)
            if name==path.name and result.st_size>0:raise OSError("final_check")
            return result
        monkeypatch.setattr(os,"stat",fail_final)
    with pytest.raises(OSError):publisher(path,{"fixture":True})
    state=("recoverable_final" if path.exists() and not temp.exists()
           else "blocked" if path.exists() or temp.exists() else "absent")
    assert state==expected


def test_acquisition_wrong_review_hash_stops_before_process(tmp_path: Path, monkeypatch):
    config=tmp_path/"config.json";authority=tmp_path/"authority.json";review=tmp_path/"review.md";prov=tmp_path/"prov";prov.mkdir()
    config.write_bytes(acq.canonical({"source_repo":acq.REPO,"source_commit":acq.COMMIT,"files":acq.FILES}))
    authority.write_bytes(acq.canonical({"status":"approved_for_exact_source_acquisition"}))
    baseline=prov/"baseline_inventory.json";baseline.write_bytes(acq.canonical({}))
    review.write_text("VERDICT: SHIP\n"+acq.sha_file(authority)+"\n"+acq.sha_file(baseline))
    monkeypatch.setattr(acq,"CONFIG",config);monkeypatch.setattr(acq,"AUTHORITY",authority)
    monkeypatch.setattr(acq,"AUTHORITY_REVIEW",review);monkeypatch.setattr(acq,"PROV",prov);monkeypatch.setattr(acq,"BASELINE",baseline)
    monkeypatch.setattr(sys,"argv",[str(ACQUISITION_SCRIPT),"--authority-review-sha256","0"*64])
    monkeypatch.setattr(acq.subprocess,"run",lambda *a,**k:(_ for _ in ()).throw(AssertionError("process invoked")))
    with pytest.raises(acq.AcquisitionFailure,match="authority_gate"):
        acq.main()


def test_acquisition_runner_has_narrow_subprocess_surface():
    import ast
    tree=ast.parse(ACQUISITION_SCRIPT.read_text(encoding="utf-8"))
    calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
           and isinstance(node.func.value,ast.Name) and node.func.value.id=="subprocess"]
    assert len(calls)==1 and calls[0].func.attr=="run"
    assert not any(keyword.arg=="shell" for keyword in calls[0].keywords)
    assert acq.validate_config(acq.expected_config()) == acq.expected_config()


def test_acquisition_mutated_argv_stops_before_process(tmp_path: Path, monkeypatch):
    config=tmp_path/"config.json";value=acq.expected_config();value["clone_argv"][0]="printf"
    config.write_bytes(acq.canonical(value))
    authority=tmp_path/"authority.json";baseline=tmp_path/"baseline.json";review=tmp_path/"review.md"
    baseline.write_bytes(acq.canonical({"training_root_entries":[]}))
    authority.write_bytes(acq.canonical({"status":"approved_for_exact_source_acquisition","artifact_sha256":{
        "scripts/acquire_msae_independent_source_v9.py":acq.sha_file(ACQUISITION_SCRIPT),
        "configs/msae_independent_source_v9/acquisition.json":acq.sha_file(config),
        acq.CARRYOVER:acq.CARRYOVER_SHA256}}))
    review.write_text("VERDICT: SHIP\n"+acq.sha_file(authority)+"\n"+acq.sha_file(baseline))
    monkeypatch.setattr(acq,"CONFIG",config);monkeypatch.setattr(acq,"AUTHORITY",authority)
    monkeypatch.setattr(acq,"AUTHORITY_REVIEW",review);monkeypatch.setattr(acq,"BASELINE",baseline)
    monkeypatch.setattr(sys,"argv",[str(ACQUISITION_SCRIPT),"--authority-review-sha256",acq.sha_file(review)])
    monkeypatch.setattr(acq.subprocess,"run",lambda *a,**k:(_ for _ in ()).throw(AssertionError("process invoked")))
    with pytest.raises(acq.AcquisitionFailure,match="acquisition_config_drift"):
        acq.main()


@pytest.mark.parametrize("blocked",("report_symlink","rejection_temp","raw_symlink"))
def test_acquisition_lstat_preflight_stops_before_process(tmp_path: Path, monkeypatch, blocked: str):
    report=tmp_path/"prov/source_acquisition.json";rejection=tmp_path/"prov/source_acquisition_rejection.json"
    raw=tmp_path/"data/msae_independent_source_v9/raw"/acq.COMMIT
    report.parent.mkdir(parents=True)
    if blocked=="report_symlink":report.symlink_to(tmp_path/"missing")
    elif blocked=="rejection_temp":rejection.with_name("."+rejection.name+".building").write_text("abandoned")
    else:
        raw.parent.parent.parent.mkdir(parents=True);raw.parent.parent.symlink_to(tmp_path/"missing",target_is_directory=True)
    monkeypatch.setattr(acq,"ROOT",tmp_path);monkeypatch.setattr(acq,"REPORT",report)
    monkeypatch.setattr(acq,"REJECTION",rejection);monkeypatch.setattr(acq,"RAW",raw)
    monkeypatch.setattr(acq,"ENTRY",report.parent/"source_acquisition_entry.json")
    with pytest.raises(acq.AcquisitionFailure,match="acquisition_target_preexists"):
        acq.require_clean_target()


def test_acquisition_failure_is_terminal_and_source_free(tmp_path: Path, monkeypatch):
    root,prov=acquisition_fixture(tmp_path,monkeypatch);acq.ENTRY.write_text("{}")
    sparse=acq.sha_bytes(("\n".join("/"+name for name in acq.FILES)+"\n").encode())
    acq.FAILURE_CONTEXT.clear();acq.FAILURE_CONTEXT.update(
        authority_manifest_sha256=acq.sha_file(acq.AUTHORITY),authority_review_sha256=acq.sha_file(acq.AUTHORITY_REVIEW),
        baseline_inventory_sha256=acq.sha_file(acq.BASELINE),config_sha256=acq.sha_file(acq.CONFIG),
        runner_sha256=acq.sha_file(ACQUISITION_SCRIPT),supplied_authority_review_sha256=acq.sha_file(acq.AUTHORITY_REVIEW),
        sparse_checkout_sha256=sparse,source_acquisition_entry_sha256=acq.sha_file(acq.ENTRY))
    acq.COMMAND_RECORDS.clear();monkeypatch.setattr(acq,"SCRATCH_CREATED",False);monkeypatch.setattr(acq,"SCRATCH_CLEANUP_OK",True)
    acq.retain_failure("fixture_failure")
    value=json.loads(acq.REJECTION.read_text())
    assert value["failure_code"]=="fixture_failure" and value["training_root_status"]=="unchanged"
    assert value["model_scoring_authorized"] is False and value["k2_or_branch_training_authorized"] is False
    assert value["terminal_process_snapshot"]["status"] in {"eligible","ineligible"}


def test_acquisition_entry_is_durable_before_first_subprocess(tmp_path: Path, monkeypatch):
    acquisition_fixture(tmp_path,monkeypatch);calls=[]
    def fail_first(argv,**_kwargs):
        calls.append(argv)
        assert acq.ENTRY.is_file() and acq.sha_file(acq.ENTRY)==acq.FAILURE_CONTEXT["source_acquisition_entry_sha256"]
        return acq.subprocess.CompletedProcess(argv,1,b"",b"fixture")
    monkeypatch.setattr(acq.subprocess,"run",fail_first)
    with pytest.raises(acq.AcquisitionFailure,match="command_failed"):
        acq.entrypoint()
    assert len(calls)==1 and acq.REJECTION.is_file()
    rejection=json.loads(acq.REJECTION.read_text())
    assert rejection["source_acquisition_entry_sha256"]==acq.sha_file(acq.ENTRY)
    assert rejection["commands"][0]["name"]=="ignore_raw"
    monkeypatch.setattr(acq.subprocess,"run",lambda *_a,**_k:(_ for _ in ()).throw(AssertionError("retried")))
    acq.entrypoint()
    assert not acq.COMMAND_RECORDS


def test_acquisition_history_drift_stops_before_entry_or_subprocess(tmp_path: Path, monkeypatch):
    root,_prov=acquisition_fixture(tmp_path,monkeypatch)
    (root/"late_history.txt").write_text("late",encoding="utf-8")
    monkeypatch.setattr(acq.subprocess,"run",
        lambda *_a,**_k:(_ for _ in ()).throw(AssertionError("process invoked")))
    with pytest.raises(acq.AcquisitionFailure,match="history_structural_drift"):
        acq.entrypoint()
    assert not acq.ENTRY.exists() and not acq.COMMAND_RECORDS


def test_acquisition_rejection_mutation_cannot_be_idempotent(tmp_path: Path, monkeypatch):
    acquisition_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(acq.subprocess,"run",lambda argv,**_kwargs:acq.subprocess.CompletedProcess(argv,1,b"",b"fixture"))
    with pytest.raises(acq.AcquisitionFailure,match="command_failed"):acq.entrypoint()
    value=json.loads(acq.REJECTION.read_text());value["model_operations_initiated_by_runner"]=1
    acq.REJECTION.write_bytes(acq.canonical(value))
    monkeypatch.setattr(acq.subprocess,"run",lambda *_a,**_k:(_ for _ in ()).throw(AssertionError("retried")))
    with pytest.raises(acq.AcquisitionFailure,match="invalid_preacquisition_state"):acq.entrypoint()


@pytest.mark.parametrize("mutation",("raw_inode","tree_digest","command_argv","command_digest","negative_count","file_digest","raw_blob"))
def test_acquisition_success_reconstructs_every_binding(tmp_path: Path,monkeypatch,mutation: str):
    report,entry_sha,manifest_sha,review_sha,baseline_sha=acquisition_success_fixture(tmp_path,monkeypatch)
    acq.validate_success_report(report,entry_sha,manifest_sha,review_sha,baseline_sha)
    changed=json.loads(json.dumps(report))
    if mutation=="raw_inode":changed["raw_directory"]["inode"]+=1
    elif mutation=="tree_digest":changed["tree_object_sha1"]="B"*40
    elif mutation=="command_argv":changed["commands"][3]["argv"][-1]="wrong"
    elif mutation=="command_digest":changed["commands"][6]["stdout_sha256"]="z"*64
    elif mutation=="negative_count":changed["commands"][0]["stdout_bytes"]=-1
    elif mutation=="file_digest":changed["files"][acq.FILES[0]]["sha256"]="A"*64
    else:
        path=acq.RAW/acq.FILES[0];payload=path.read_bytes();replacement=b"X"+payload[1:]
        os.chmod(path,0o644);path.write_bytes(replacement);os.chmod(path,0o444)
        changed["files"][acq.FILES[0]]["sha256"]=acq.sha_bytes(replacement)
    with pytest.raises(acq.AcquisitionFailure,match="invalid_preacquisition_state"):
        acq.validate_success_report(changed,entry_sha,manifest_sha,review_sha,baseline_sha)


def test_acquisition_recovers_complete_final_after_parent_fsync_uncertainty(tmp_path: Path,monkeypatch):
    report,_entry_sha,manifest_sha,review_sha,baseline_sha=acquisition_success_fixture(tmp_path,monkeypatch)
    real_fsync=os.fsync;calls=0
    def fail_final_parent_fsync(fd: int):
        nonlocal calls
        calls+=1
        if calls==3:raise OSError("parent_fsync")
        return real_fsync(fd)
    monkeypatch.setattr(os,"fsync",fail_final_parent_fsync)
    with pytest.raises(OSError,match="parent_fsync"):acq.atomic_json(acq.REPORT,report)
    assert acq.REPORT.is_file() and not acq.REPORT.with_name("."+acq.REPORT.name+".building").exists()
    monkeypatch.setattr(os,"fsync",real_fsync)
    monkeypatch.setattr(acq.subprocess,"run",
        lambda *_a,**_k:(_ for _ in ()).throw(AssertionError("acquisition retried")))
    assert acq.preflight_state(manifest_sha,review_sha,baseline_sha)=="success"


def test_acquisition_noncanonical_success_is_not_idempotent(tmp_path: Path,monkeypatch):
    report,entry_sha,manifest_sha,review_sha,baseline_sha=acquisition_success_fixture(tmp_path,monkeypatch)
    acq.REPORT.write_text(json.dumps(report,indent=2),encoding="utf-8")
    with pytest.raises(acq.AcquisitionFailure,match="invalid_preacquisition_state"):
        acq.preflight_state(manifest_sha,review_sha,baseline_sha)


def test_acquisition_scratch_cleanup_failure_has_no_terminal_outcome(tmp_path: Path, monkeypatch):
    acquisition_fixture(tmp_path,monkeypatch);scratch=tmp_path/"scratch";real_rmtree=acq.shutil.rmtree
    def make_scratch(**_kwargs):scratch.mkdir();return str(scratch)
    monkeypatch.setattr(acq.tempfile,"mkdtemp",make_scratch)
    monkeypatch.setattr(acq.subprocess,"run",lambda argv,**_kwargs:acq.subprocess.CompletedProcess(argv,1,b"",b"fixture"))
    monkeypatch.setattr(acq.shutil,"rmtree",lambda _path:(_ for _ in ()).throw(OSError("cleanup")))
    with pytest.raises(acq.AcquisitionFailure,match="scratch_cleanup_failed"):acq.entrypoint()
    assert acq.ENTRY.is_file() and not acq.REPORT.exists() and not acq.REJECTION.exists() and scratch.exists()
    real_rmtree(scratch)


@pytest.mark.parametrize("obstruction",("entry_temp","report_final","report_temp","rejection_final","rejection_temp"))
def test_acquisition_invalid_preflight_never_starts_or_retries(tmp_path: Path, monkeypatch, obstruction: str):
    acquisition_fixture(tmp_path,monkeypatch)
    paths={
        "entry_temp":acq.ENTRY.with_name("."+acq.ENTRY.name+".building"),
        "report_final":acq.REPORT,"report_temp":acq.REPORT.with_name("."+acq.REPORT.name+".building"),
        "rejection_final":acq.REJECTION,
        "rejection_temp":acq.REJECTION.with_name("."+acq.REJECTION.name+".building"),
    }
    paths[obstruction].write_text("invalid")
    monkeypatch.setattr(acq.subprocess,"run",lambda *_a,**_k:(_ for _ in ()).throw(AssertionError("process invoked")))
    with pytest.raises(acq.AcquisitionFailure,match="invalid_preacquisition_state"):
        acq.entrypoint()
    assert not acq.ENTRY.exists() and not acq.COMMAND_RECORDS


@pytest.mark.parametrize("mutation",("extra_file","file_symlink","hardlink","private_file"))
def test_pre_payload_namespace_is_exact(tmp_path: Path, monkeypatch, mutation: str):
    raw=tmp_path/"data/msae_independent_source_v9/raw"/m.COMMIT;raw.mkdir(parents=True)
    monkeypatch.setattr(m,"RAW",raw)
    os.chmod(raw.parent.parent,0o700);os.chmod(raw.parent,0o700);os.chmod(raw,0o555)
    for name in [*m.SOURCE_FILES.values(),"LICENSE.txt"]:
        path=raw/name;path.write_text("x");os.chmod(path,0o444)
    monkeypatch.setattr(m,"RAW",raw)
    m.verify_pre_payload_v9_namespace()
    if mutation=="private_file":
        private=raw.parent.parent/"private";private.mkdir();(private/"unexpected.txt").write_text("x")
        code="v9_namespace_extra_path"
    else:
        os.chmod(raw,0o755);extra=raw/"extra.txt"
        if mutation=="extra_file":extra.write_text("x")
        elif mutation=="file_symlink":extra.symlink_to(raw/"LICENSE.txt")
        else:os.link(raw/"LICENSE.txt",extra)
        os.chmod(raw,0o555);code="raw_file_set_drift"
    with pytest.raises(m.GateFailure,match=code):
        m.verify_pre_payload_v9_namespace()


def test_lexical_support_is_hashed():
    value = "MSAE_V9_SECRET_LEMMA_9d3e"
    item = m.public_label("lemma_identity", value)
    assert value not in json.dumps(item)
    assert item == hashlib.sha256(("msae-v9/lemma\0" + value).encode()).hexdigest()


def test_quarantine_inventory_is_lstat_only(tmp_path: Path, monkeypatch):
    q = tmp_path / "q.jsonl"
    q.write_text("MSAE_V9_MUST_NOT_OPEN")
    called = []
    real_open = Path.open
    def guarded(self, *args, **kwargs):
        if self == q:
            called.append(True)
            raise AssertionError("quarantine opened")
        return real_open(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded)
    item = m.inventory_one(q, "q.jsonl", {"q.jsonl"})
    assert item["sha256"] is None
    assert item["adapter"] == "quarantine_lstat_only"
    assert item["content_reads"] == 0
    assert not called


def test_static_no_neural_contract():
    assert m.validate_static_contract(SCRIPT) == []


def test_build_ready_ends_with_full_terminal_verification():
    import ast
    tree=ast.parse(SCRIPT.read_text(encoding="utf-8"))
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=="build_ready")
    final=function.body[-1]
    assert (isinstance(final,ast.Expr) and isinstance(final.value,ast.Call)
            and isinstance(final.value.func,ast.Name) and final.value.func.id=="verify_terminal")


def test_history_snapshot_binds_binary_text_and_quarantine(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m, "ROOT", tmp_path)
    text_path = tmp_path / "history.txt"
    quarantine_path = tmp_path / "quarantine.jsonl"
    binary_path = tmp_path / "cache.pyc"
    text_path.write_text("historical text", encoding="utf-8")
    quarantine_path.write_text("must remain unopened", encoding="utf-8")
    binary_path.write_bytes(b"old bytecode")

    def entry(path: Path, disposition: str) -> dict[str, object]:
        st = path.lstat()
        return {
            "path": path.relative_to(tmp_path).as_posix(),
            "disposition": disposition,
            "size": st.st_size,
            "device": st.st_dev,
            "inode": st.st_ino,
            "mode": st.st_mode & 0o777,
            "nlink": st.st_nlink,
            "mtime_ns": st.st_mtime_ns,
            "sha256": m.sha_file(path) if disposition != "quarantine" else None,
        }

    text_entry = entry(text_path, "text_scanned")
    quarantine_entry = entry(quarantine_path, "quarantine")
    binary_entry = entry(binary_path, "binary_unscanned")
    inventory = {"entries": [text_entry, quarantine_entry, binary_entry]}

    replacement = tmp_path / "replacement.pyc"
    replacement.write_bytes(b"new regenerated bytecode")
    os.replace(replacement, binary_path)
    with pytest.raises(m.GateFailure, match="history_snapshot_drift"):
        m._verify_history_snapshot(inventory)

    text_path.write_text("changed historical text", encoding="utf-8")
    with pytest.raises(m.GateFailure, match="history_snapshot_drift"):
        m._verify_history_snapshot(inventory)

    text_path.unlink()
    text_path.write_text("historical text", encoding="utf-8")
    inventory = {"entries": [entry(text_path, "text_scanned"), quarantine_entry, binary_entry]}
    quarantine_path.write_text("changed quarantine metadata", encoding="utf-8")
    with pytest.raises(m.GateFailure, match="history_snapshot_drift"):
        m._verify_history_snapshot(inventory)


def test_history_snapshot_rejects_new_files_and_hardlinks(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m,"ROOT",tmp_path)
    path=tmp_path/"history.txt";path.write_text("history")
    st=path.lstat();entry={"path":"history.txt","disposition":"text_scanned","size":st.st_size,
        "device":st.st_dev,"inode":st.st_ino,"mode":st.st_mode&0o777,"nlink":st.st_nlink,
        "mtime_ns":st.st_mtime_ns,"sha256":m.sha_file(path)}
    inventory={"entries":[entry]}
    (tmp_path/"new.txt").write_text("late")
    with pytest.raises(m.GateFailure,match="history_structural_addition"):
        m._verify_history_snapshot(inventory)
    (tmp_path/"new.txt").unlink();os.link(path,tmp_path/"alias.txt")
    with pytest.raises(m.GateFailure,match="history_structural_addition"):
        m._verify_history_snapshot(inventory)


def test_payload_zero_write_fails_without_publication(tmp_path: Path, monkeypatch):
    private=tmp_path/"private"
    monkeypatch.setattr(os,"write",lambda _fd,_data:0)
    with pytest.raises(OSError,match="short payload write"):
        m.publish_private_jsonl(private,"payload.jsonl",[{"x":1}])
    assert not (private/"payload.jsonl").exists()
    assert not (private/".payload.jsonl.building").exists()


def publish_scientific_terminal_with_recoverable_fault(
        path: Path, value: dict[str, object], fault: str, monkeypatch) -> None:
    real_fsync,real_stat=os.fsync,os.stat;calls=0
    if fault=="parent_fsync":
        def fail_parent_fsync(fd: int):
            nonlocal calls
            calls+=1
            if calls==3:raise OSError("parent_fsync")
            return real_fsync(fd)
        monkeypatch.setattr(os,"fsync",fail_parent_fsync)
    elif fault=="final_check":
        def fail_final_check(name,*args,**kwargs):
            result=real_stat(name,*args,**kwargs)
            if name==path.name and result.st_size>0:raise OSError("final_check")
            return result
        monkeypatch.setattr(os,"stat",fail_final_check)
    else:raise AssertionError(fault)
    with pytest.raises(OSError,match=fault):m.write_json(path,value)
    monkeypatch.setattr(os,"fsync",real_fsync);monkeypatch.setattr(os,"stat",real_stat)
    assert path.is_file() and not path.with_name("."+path.name+".building").exists()


def scientific_terminal_fixture(tmp_path: Path, monkeypatch):
    prov=tmp_path/"reports/provenance/msae_independent_source_v9";prov.mkdir(parents=True)
    private=tmp_path/"data/msae_independent_source_v9/private"
    monkeypatch.setattr(m,"ROOT",tmp_path);monkeypatch.setattr(m,"PROV",prov)
    monkeypatch.setattr(m,"PRIVATE",private)
    monkeypatch.setattr(m,"RAW",tmp_path/"data/msae_independent_source_v9/raw"/m.COMMIT)
    for rel in ("docs/plan-msae-independent-source-v9.md",
                "reports/adversarial/msae_independent_source_v9_plan_review.md",
                "reports/adversarial/msae_independent_source_v9_preacquisition_authority_review.md"):
        path=tmp_path/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(rel,encoding="utf-8")
    snapshot={"schema_version":"msae_independent_source_v9_process_snapshot_v1",
        "observation_scope":"point_in_time_proc_snapshot","forbidden_tokens":list(m.FORBIDDEN_PROCESS_TOKENS),
        "process_count":0,"entries":[],"forbidden_identity_count":0,"status":"eligible"}
    empty=m.sha_bytes(m.canonical_bytes([]))
    baseline={"entries":[],"entries_sha256":empty,"history_inputs_sha256":empty,
              "training_root_entries":[],"training_root_entries_sha256":empty}
    m.write_json(prov/"baseline_inventory.json",baseline)
    m.write_json(prov/"preacquisition_authority_manifest.json",{"fixture":True})
    m.write_json(prov/"source_acquisition_entry.json",{"fixture":True})
    files={name:{"size":1,"sha256":"a"*64,"git_blob_sha1":"b"*40,"mode":0o444,"nlink":1}
           for name in [*m.SOURCE_FILES.values(),"LICENSE.txt"]}
    acquisition={"files":files};m.write_json(prov/"source_acquisition.json",acquisition)
    m.write_json(prov/"historical_source_registry.json",{"fixture":True})
    monkeypatch.setattr(m,"_validate_inventory_artifact",lambda *_a,**_k:None)
    monkeypatch.setattr(m,"validate_history_registry_binding",lambda *_a,**_k:empty)
    monkeypatch.setattr(m,"_verify_predecessor_and_raw",lambda *a,**k:acquisition)
    monkeypatch.setattr(m,"_verify_history_snapshot",lambda *_a,**_k:None)
    monkeypatch.setattr(m,"verify_training_roots",lambda *_a,**_k:None)
    monkeypatch.setattr(m,"process_snapshot",lambda:snapshot)
    monkeypatch.setattr(m,"_post_baseline_inventory",
        lambda _inv,state,self_path=None,verify_raw_hashes=True:{
            "schema_version":"msae_independent_source_v9_post_baseline_inventory_v1",
            "state":state,"entries":[]})
    return prov,private,baseline,acquisition,snapshot


@pytest.mark.parametrize("terminal_kind",("B0","B1"))
@pytest.mark.parametrize("fault",("final_check","parent_fsync"))
def test_scientific_rejection_publisher_fault_recovers_through_real_terminal_verifier(
        tmp_path: Path, monkeypatch, terminal_kind: str, fault: str):
    prov,_private,baseline,acquisition,snapshot=scientific_terminal_fixture(tmp_path,monkeypatch)
    history=m._eligible_history_recensus(baseline);training=m._eligible_training_recensus(baseline)
    if terminal_kind=="B0":
        m.retain_preflight_rejection("history_structural_addition",history,training,snapshot)
        path=prov/"preflight_rejection.json"
    else:
        m.publish_scientific_entry(baseline,acquisition,snapshot,history,training)
        monkeypatch.setattr(m,"RAW_FILE_OPEN_COUNT",1)
        m.retain_rejection("fixture_failure")
        path=prov/"rejection.json"
    monkeypatch.setattr(m,"_history_recensus",lambda *_a,**_k:history)
    monkeypatch.setattr(m,"_training_recensus",lambda *_a,**_k:training)
    value=m.strict_json(path);path.unlink()
    publish_scientific_terminal_with_recoverable_fault(path,value,fault,monkeypatch)
    m.verify_terminal()
    path.with_name("."+path.name+".building").write_text("partial",encoding="utf-8")
    with pytest.raises(m.GateFailure,match="terminal_state_cardinality"):m.verify_terminal()


def test_verify_terminal_b1_enforces_custody_inventory_and_payload_state(tmp_path: Path, monkeypatch):
    prov,private,baseline,acquisition,snapshot=scientific_terminal_fixture(tmp_path,monkeypatch)
    history=m._eligible_history_recensus(baseline);training=m._eligible_training_recensus(baseline)
    m.publish_scientific_entry(baseline,acquisition,snapshot,history,training)
    monkeypatch.setattr(m,"_history_recensus",lambda *_a,**_k:history)
    monkeypatch.setattr(m,"_training_recensus",lambda *_a,**_k:training)
    monkeypatch.setattr(m,"RAW_FILE_OPEN_COUNT",1)
    m.retain_rejection("fixture_failure");path=prov/"rejection.json"
    m.verify_terminal()
    os.chmod(path,0o666)
    with pytest.raises(m.GateFailure,match="terminal_final_custody"):m.verify_terminal()
    os.chmod(path,0o644);alias=tmp_path/"rejection-alias.json";os.link(path,alias)
    with pytest.raises(m.GateFailure,match="terminal_final_custody"):m.verify_terminal()
    alias.unlink()
    private.mkdir(parents=True);(private/"blind_payload.jsonl").write_text("unexpected",encoding="utf-8")
    with pytest.raises(m.GateFailure,match="rejection_verification"):m.verify_terminal()


def test_entry_only_and_any_abandoned_temp_are_case_c(tmp_path: Path, monkeypatch):
    prov,private,baseline,acquisition,snapshot=scientific_terminal_fixture(tmp_path,monkeypatch)
    m.publish_scientific_entry(baseline,acquisition,snapshot,
                               m._eligible_history_recensus(baseline),
                               m._eligible_training_recensus(baseline))
    with pytest.raises(m.GateFailure,match="terminal_state_cardinality"):m.verify_terminal()
    temp=prov/".support.json.building";temp.write_text("partial-public",encoding="utf-8")
    with pytest.raises(m.GateFailure,match="terminal_state_cardinality"):m.verify_terminal()
    temp.unlink();private.mkdir(parents=True);(private/".blind_payload.jsonl.building").write_text("opaque")
    with pytest.raises(m.GateFailure,match="terminal_state_cardinality"):m.verify_terminal()


@pytest.mark.parametrize("terminal_publish_fault",("final_check","parent_fsync"))
def test_verify_terminal_complete_synthetic_success(tmp_path: Path, monkeypatch, terminal_publish_fault: str):
    prov=tmp_path/"reports/provenance/msae_independent_source_v9";prov.mkdir(parents=True)
    private=tmp_path/"data/msae_independent_source_v9/private";private.mkdir(parents=True)
    os.chmod(private,0o700)
    monkeypatch.setattr(m,"ROOT",tmp_path);monkeypatch.setattr(m,"PROV",prov);monkeypatch.setattr(m,"PRIVATE",private)
    for rel in ("docs/plan-msae-independent-source-v9.md","reports/adversarial/msae_independent_source_v9_plan_review.md",
                "scripts/acquire_msae_independent_source_v9.py","tests/test_prepare_msae_independent_source_v9.py"):
        path=tmp_path/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(rel)
    h="a"*64;h2="b"*64;empty_sha=m.sha_bytes(m._canonical_ascii_bytes([]))
    split_entries=[]
    for rank,panel,prefix,key in ((0,"C1","a",h),(1,"C2","b",h2)):
        split_entries.extend({"sent_id":f"{prefix}{index}","panel":panel,"group_rank":rank,
            "within_group_rank":index,"group_key_sha256":key,"group_id_sha256":key,
            "source_record_sha256":h} for index in range(20))
    split={"schema_version":"msae_independent_source_v9_split_manifest_v1","source_commit":m.COMMIT,
           "upstream_partition":"test","test_group_policy":"sent_id_as_group",
           "split_algorithm":"sha256-canonical-json-group-v1-even-C1-odd-C2",
           "pre_dedup_group_count":2,"retained_group_count":2,"fully_removed_group_count":0,
           "group_count":2,"C1_group_count":1,"C2_group_count":1,"record_count":40,
           "C1_count":20,"C2_count":20,"entries":split_entries}
    role_entries=lambda prefix:[{"zero_based_rank":index,"sent_id":f"{prefix}{index}",
                                "source_record_sha256":h} for index in range(20)]
    roles={"schema_version":"msae_independent_source_v9_role_manifest_v1","source_commit":m.COMMIT,"roles":{
        "discovery":{"upstream_partition":"train","record_count":20,"entries":role_entries("d")},
        "calibration":{"upstream_partition":"dev","record_count":20,"entries":role_entries("c")}}}
    partition=lambda sentences:{"integer_tokens":sentences,"multiword_rows":0,"empty_node_rows":0,
                                "sentences":sentences,"sha256":h}
    source={"schema_version":"msae_independent_source_v9_source_manifest_v1","source_commit":m.COMMIT,
            "source_text_published":False,"partitions":{"train":partition(20),"dev":partition(20),"test":partition(40)}}
    dedup_role=lambda upstream,count:{"upstream_partition":upstream,"input_count":count,"retained_count":count,
        "within_partition_dropped_count":0,"within_partition_dropped_ids_sha256":h,
        "cross_partition_dropped_count":0,"cross_partition_dropped_ids_sha256":h}
    dedup={"schema_version":"msae_independent_source_v9_dedup_v1","roles":{
        "discovery":dedup_role("train",20),"calibration":dedup_role("dev",20),"test":dedup_role("test",40)},
        "cross_partition_normalized_group_count":0,"source_text_published":False,
        "test_groups":{"pre_dedup_group_count":2,"retained_group_count":2,"fully_removed_group_count":0,
                       "fully_removed_group_ids_sha256":h}}
    task_record={"eligible":True,"retained_class_count":2,"distinct_utterances_by_class":{"a":20,"b":20}}
    support_role=lambda count:{"utterance_count":count,"tasks":{task:dict(task_record) for task in m.TASKS}}
    support={"schema_version":"msae_independent_source_v9_support_v1","floor_distinct_utterances":20,
        "status":"eligible","roles":{"discovery":support_role(20),"calibration":support_role(20),
                                        "C1":support_role(20),"C2":support_role(20)},
        "all_role_task_intersection":sorted(m.TASKS),
        "unsupported_tasks":["neutral_prefix_offset","entity_binary","entity_type","source_genre"]}
    snapshot={"schema_version":"msae_independent_source_v9_process_snapshot_v1",
        "observation_scope":"point_in_time_proc_snapshot","forbidden_tokens":list(m.FORBIDDEN_PROCESS_TOKENS),
        "process_count":0,"entries":[],"forbidden_identity_count":0,"status":"eligible"}
    baseline={"schema_version":"msae_independent_source_v9_baseline_inventory_v1",
        "baseline_head":"7e1a6fc7a26a870a4edcf29c96b7cdf3cdbd7faa","entry_count":0,"counts":{},
        "quarantine_content_reads":0,"entries":[],"authority_expected_absent":[],
        "entries_sha256":m.sha_bytes(m.canonical_bytes([])),"history_inputs_sha256":empty_sha,
        "status":"eligible","process_snapshot":snapshot,"training_root_entries":[],
        "training_root_entries_sha256":m.sha_bytes(m.canonical_bytes([]))}
    raw=tmp_path/"data/msae_independent_source_v9/raw"/m.COMMIT;raw.mkdir(parents=True)
    monkeypatch.setattr(m,"RAW",raw)
    (raw/"LICENSE.txt").write_text("fixture license",encoding="utf-8")
    census_files={}
    for role,name in m.SOURCE_FILES.items():
        count=40 if role=="test" else 20
        census_files[name]={"marker_count":0,"sentence_count":count,"group_count":count,
            "empty_group_count":0,"orphan_sentence_count":0,"duplicate_group_count":0,
            "group_id_set_sha256":h}
    census={"schema_version":"msae_independent_source_v9_document_group_census_v1","newdoc_marker_count":0,
        "files":census_files,"test_group_policy":"sent_id_as_group","cross_partition_group_id_count":0,
        "natural_unit":"sentence","split_group_unit":"explicit_document_or_sent_id_fallback",
        "document_speaker_cluster_inference_authorized":False,"status":"eligible"}
    evidence={"eligible":True,"positive_occurrence_count":1,
        "positive_phrase_counts":{" ".join(item):(1 if item==m.LICENSE_PHRASES[0] else 0) for item in m.LICENSE_PHRASES},
        "positive_url_counts":{},"contradiction_counts":{" ".join(item):0 for item in m.LICENSE_CONTRADICTIONS},
        "contradiction_count":0}
    license_value={"schema_version":"msae_independent_source_v9_license_v1","license_id":"CC-BY-SA-4.0",
        "license_path":"LICENSE.txt","license_sha256":m.sha_file(raw/"LICENSE.txt"),
        "license_url":"https://creativecommons.org/licenses/by-sa/4.0/",
        "evidence":{"LICENSE.txt":evidence},"obligations":["attribution","share_alike"],
        "raw_committed":False,"payload_committed":False,"contradiction_count":0,"status":"eligible"}
    family={"schema_version":"msae_independent_source_v9_source_family_v1","status":"eligible",
        "disposition":"project_source_use_unseen_before_v9","content_occurrence_count":0,"content_occurrences":[],
        "pathname_occurrence_count":0,"pathname_occurrences":[],"whole_file_digest_matches":[],
        "history_inputs_sha256":empty_sha,"source_text_published":False}
    registry={"schema_version":"msae_independent_source_v9_historical_source_registry_v1",
        "status":"frozen_preacquisition","domain_utf8":"msae-v9/pedigree","inputs":[],"input_count":0,
        "inputs_sha256":empty_sha,"overbound_json_source_key_construct_count":0}
    pedigree={"schema_version":"msae_independent_source_v9_candidate_pedigree_v1",
        "registry_sha256":"PLACEHOLDER","candidate_identifier_count":1,"candidate_identifier_sha256":[h],
        "candidate_file_identifier_counts":{name:0 for name in (*m.SOURCE_FILES.values(),"LICENSE.txt")},
        "candidate_file_identifier_sha256":{name:[] for name in (*m.SOURCE_FILES.values(),"LICENSE.txt")},
        "allowed_shared_identifier_sha256":[],"blocking_identifier_sha256":[],"blocking_identifier_count":0,
        "source_prose_published":False,"status":"eligible"}
    screen={"schema_version":"msae_independent_source_v9_preacquisition_alias_screen_v2",
        "history_input_count":0,"history_inputs_sha256":empty_sha,"history_registry_sha256":"PLACEHOLDER",
        "content_occurrence_count":0,"pathname_occurrence_count":0,"source_use_evidence_count":0,
        "status":"no_project_source_use_evidence"}
    values={
        "baseline_inventory.json":baseline,
        "source_acquisition_entry.json":{"schema_version":"msae_independent_source_v9_source_acquisition_entry_v1"},
        "source_acquisition.json":{"schema_version":"msae_independent_source_v9_source_acquisition_v1"},
        "scientific_preparation_entry.json":{"schema_version":"msae_independent_source_v9_scientific_preparation_entry_v1"},
        "source_family.json":family,"candidate_pedigree.json":pedigree,"license.json":license_value,
        "document_group_census.json":census,"source_manifest.json":source,"dedup.json":dedup,
        "history_manifest.json":baseline,
        "history_overlap.json":{"schema_version":"msae_independent_source_v9_history_overlap_v1",
            "baseline_inventory_sha256":"PLACEHOLDER","history_entries_sha256":baseline["entries_sha256"],
            "history_unit_count":0,"history_adapter_census":{},"candidate_utterance_count":80,
            "blocking_collision_count":0,"blocking_collisions":[],"quarantine_content_reads":0,
            "opaque_binary_history_count":0,"status":"eligible"},
        "cross_role_overlap.json":{"schema_version":"msae_independent_source_v9_cross_role_overlap_v1",
            "blocking_collision_count":0,"blocking_collisions":[],"status":"eligible"},
        "support.json":support,"role_manifest.json":roles,"split_manifest.json":split,
        "post_process_snapshot.json":snapshot,"preacquisition_alias_screen.json":screen,
        "historical_source_registry.json":registry,
        "preacquisition_authority_manifest.json":{"schema_version":"msae_independent_source_v9_preacquisition_authority_v1"},
    }
    m.write_json(prov/"historical_source_registry.json",registry)
    screen["history_registry_sha256"]=m.sha_file(prov/"historical_source_registry.json")
    pedigree["registry_sha256"]=screen["history_registry_sha256"]
    for name,value in values.items():
        if name not in {"historical_source_registry.json","history_overlap.json"}:m.write_json(prov/name,value)
    values["history_overlap.json"]["baseline_inventory_sha256"]=m.sha_file(prov/"baseline_inventory.json")
    m.write_json(prov/"history_overlap.json",values["history_overlap.json"])
    payload=private/"blind_payload.jsonl";payload.write_bytes(b"opaque\n");os.chmod(payload,0o600);ps=payload.lstat()
    bindings={name:m.sha_file(prov/name) for name in values}
    post_inventory={"schema_version":"msae_independent_source_v9_post_baseline_inventory_v1",
                    "state":"B2","entries":[]}
    seal={"schema_version":"msae_independent_source_v9_seal_v1",
          "status":"ready_independently_maintained_non_atis_source_pre_v8_history_screened",
          "source_status":"no_project_source_use_evidence_before_v8_subject_to_enumerated_exclusions",
          "source_maintenance_relation":"independently_maintained_official_non_project_repository",
          "source_family_relation":"non_atis",
          "project_history_boundary":"no_project_source_use_evidence_before_v8_subject_to_enumerated_exclusions",
          "v8_candidate_control_carryover_authority_sha256":m.CARRYOVER_SHA256,
          "researcher_unawareness_claimed":False,"model_pretraining_independence_claimed":False,
          "global_candidate_content_absence_claimed":False,"general_content_separation_claimed":False,
          "independent_replication_claimed":False,"model_scoring_completed":False,
          "scientific_preparation_entry_sha256":m.sha_file(prov/"scientific_preparation_entry.json"),
          "post_baseline_inventory":post_inventory,
          "plan_sha256":m.sha_file(tmp_path/"docs/plan-msae-independent-source-v9.md"),
          "plan_review_sha256":m.sha_file(tmp_path/"reports/adversarial/msae_independent_source_v9_plan_review.md"),
          "program_sha256":m.sha_file(SCRIPT),
          "acquisition_runner_sha256":m.sha_file(tmp_path/"scripts/acquire_msae_independent_source_v9.py"),
          "test_sha256":m.sha_file(tmp_path/"tests/test_prepare_msae_independent_source_v9.py"),
          "artifact_sha256":bindings,
          "payload":{"path":"data/msae_independent_source_v9/private/blind_payload.jsonl",
                     "sha256":m.sha_file(payload),"size":ps.st_size,"record_count":40,"mode":0o600,"nlink":1},
          "model_operations_initiated_by_builder":0,"gpu_queries_initiated_by_builder":0,
          "training_runs_initiated_by_builder":0,
          "source_content_reported":False,"model_scoring_authorized":False,
          "k2_or_branch_training_authorized":False,"stage_c_authorized":False,
          "external_observation_scope":"baseline_and_terminal_proc_snapshots_plus_training_root_diff",
          "unsupported_tasks":["neutral_prefix_offset","entity_binary","entity_type","source_genre"],
          "opaque_binary_history_excluded":True,"document_speaker_cluster_inference_authorized":False}
    seal_sha=m.sha_bytes(m.canonical_file_bytes(seal))
    m.write_json(prov/"no_training_gate.json",{"schema_version":"msae_independent_source_v9_no_training_gate_v1",
        "status":"pending_terminal_seal","terminal_status_if_seal_matches":seal["status"],"seal_sha256":seal_sha,
        "scientific_preparation_entry_sha256":seal["scientific_preparation_entry_sha256"],
        "model_scoring_authorized":False,"k2_or_branch_training_authorized":False,"stage_c_authorized":False})
    publish_scientific_terminal_with_recoverable_fault(
        prov/"seal.json",seal,terminal_publish_fault,monkeypatch)
    monkeypatch.setattr(m,"_verify_predecessor_and_raw",lambda *_a,**_k:{})
    monkeypatch.setattr(m,"_validate_inventory_artifact",lambda *_a,**_k:None)
    recensus_history=m._eligible_history_recensus(baseline)
    recensus_training=m._eligible_training_recensus(baseline)
    monkeypatch.setattr(m,"_verify_terminal_entry",lambda _baseline:{
        "history_recensus":recensus_history,"training_recensus":recensus_training})
    monkeypatch.setattr(m,"_post_baseline_inventory",lambda *_a,**_k:post_inventory)
    monkeypatch.setattr(m,"validate_scientific_artifacts",lambda **_k:None)
    monkeypatch.setattr(m,"validate_history_registry_binding",lambda *_a,**_k:empty_sha)
    closure_calls=[]
    monkeypatch.setattr(m,"_verify_terminal_recensuses",
                        lambda *_a,**_k:closure_calls.append("recensus"))
    m.verify_terminal()
    assert closure_calls==["recensus"]
    os.chmod(prov/"seal.json",0o666)
    with pytest.raises(m.GateFailure,match="terminal_final_custody"):m.verify_terminal()
    os.chmod(prov/"seal.json",0o644)
    alias=tmp_path/"seal-alias.json";os.link(prov/"seal.json",alias)
    with pytest.raises(m.GateFailure,match="terminal_final_custody"):m.verify_terminal()
    alias.unlink()
    (prov/".seal.json.building").write_text("partial",encoding="utf-8")
    with pytest.raises(m.GateFailure,match="terminal_state_cardinality"):m.verify_terminal()
    (prov/".seal.json.building").unlink()
    monkeypatch.setattr(m,"_verify_terminal_recensuses",
        lambda *_a,**_k:(_ for _ in ()).throw(m.GateFailure("history_recensus_drift")))
    with pytest.raises(m.GateFailure,match="history_recensus_drift"):m.verify_terminal()
    monkeypatch.setattr(m,"_verify_terminal_recensuses",lambda *_a,**_k:None)
    (prov/"seal.json").write_text(json.dumps(seal,indent=2),encoding="utf-8")
    with pytest.raises(m.GateFailure,match="noncanonical_public_json"):m.verify_terminal()
    (prov/"seal.json").write_bytes(m.canonical_file_bytes(seal))
    seal["model_operations_initiated_by_builder"]=1
    (prov/"seal.json").write_bytes(m.canonical_file_bytes(seal))
    with pytest.raises(m.GateFailure,match="seal_verification"):m.verify_terminal()
