from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts/prepare_msae_independent_source_v5.py"
ACQUISITION_SCRIPT = Path(__file__).parents[1] / "scripts/acquire_msae_independent_source_v5.py"
_spec = importlib.util.spec_from_file_location("msae_v5", SCRIPT)
assert _spec and _spec.loader
m = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = m
_spec.loader.exec_module(m)
_acq_spec = importlib.util.spec_from_file_location("msae_v5_acquisition", ACQUISITION_SCRIPT)
assert _acq_spec and _acq_spec.loader
acq = importlib.util.module_from_spec(_acq_spec)
sys.modules[_acq_spec.name] = acq
_acq_spec.loader.exec_module(acq)


def sample_conllu() -> bytes:
    return b"""# sent_id = s1\n# text = A AB Ab a-b ...\n1\tA\ta\tNOUN\t_\tNumber=Sing\t0\troot\t_\t_\n2\tAB\tab\tNOUN\t_\tNumber=Plur\t1\tnmod:poss\t_\t_\n3-4\tAb a-b\t_\t_\t_\t_\t_\t_\t_\t_\n3\tAb\tab\tADJ\t_\t_\t2\tamod\t_\t_\n3.1\tghost\tghost\tX\t_\t_\t_\t_\t_\t_\n4\ta-b\ta-b\tNOUN\t_\t_\t2\tconj\t_\t_\n5\t...\t...\tPUNCT\t_\t_\t3\tpunct\t_\t_\n\n"""


def acquisition_fixture(tmp_path: Path, monkeypatch):
    root=tmp_path;prov=root/"reports/provenance/msae_independent_source_v5";prov.mkdir(parents=True)
    config=root/"configs/msae_independent_source_v5/acquisition.json";config.parent.mkdir(parents=True)
    config.write_bytes(acq.canonical(acq.expected_config()))
    baseline=prov/"baseline_inventory.json";baseline.write_bytes(acq.canonical({"training_root_entries":[]}))
    authority=prov/"preacquisition_authority_manifest.json"
    authority.write_bytes(acq.canonical({"status":"approved_for_exact_source_acquisition","artifact_sha256":{
        "scripts/acquire_msae_independent_source_v5.py":acq.sha_file(ACQUISITION_SCRIPT),
        "configs/msae_independent_source_v5/acquisition.json":acq.sha_file(config)}}))
    review=root/"reports/adversarial/msae_independent_source_v5_preacquisition_authority_review.md";review.parent.mkdir(parents=True)
    review.write_text("VERDICT: SHIP\n"+acq.sha_file(authority)+"\n"+acq.sha_file(baseline))
    monkeypatch.setattr(acq,"ROOT",root);monkeypatch.setattr(acq,"PROV",prov);monkeypatch.setattr(acq,"CONFIG",config)
    monkeypatch.setattr(acq,"BASELINE",baseline);monkeypatch.setattr(acq,"AUTHORITY",authority)
    monkeypatch.setattr(acq,"AUTHORITY_REVIEW",review);monkeypatch.setattr(acq,"ENTRY",prov/"source_acquisition_entry.json")
    monkeypatch.setattr(acq,"REPORT",prov/"source_acquisition.json");monkeypatch.setattr(acq,"REJECTION",prov/"source_acquisition_rejection.json")
    monkeypatch.setattr(acq,"RAW",root/"data/msae_independent_source_v5/raw"/acq.COMMIT)
    monkeypatch.setattr(sys,"argv",[str(ACQUISITION_SCRIPT),"--authority-review-sha256",acq.sha_file(review)])
    return root,prov


def acquisition_success_fixture(tmp_path: Path,monkeypatch):
    _root,_prov=acquisition_fixture(tmp_path,monkeypatch);config=acq.expected_config()
    manifest_sha=acq.sha_file(acq.AUTHORITY);review_sha=acq.sha_file(acq.AUTHORITY_REVIEW);baseline_sha=acq.sha_file(acq.BASELINE)
    entry={"schema_version":"msae_independent_source_v5_source_acquisition_entry_v1","status":"entered",
        "authority_manifest_sha256":manifest_sha,"authority_review_sha256":review_sha,
        "baseline_inventory_sha256":baseline_sha,"config_sha256":acq.sha_file(acq.CONFIG),
        "runner_sha256":acq.sha_file(ACQUISITION_SCRIPT),"source_repo":acq.REPO,"source_commit":acq.COMMIT,
        "files":acq.FILES,"subprocesses_started":0,"model_scoring_authorized":False,
        "k2_or_branch_training_authorized":False,"stage_c_authorized":False}
    acq.ENTRY.write_bytes(acq.canonical(entry));entry_sha=acq.sha_file(acq.ENTRY)
    raw=acq.RAW;raw.mkdir(parents=True);os.chmod(raw.parent.parent,0o700);os.chmod(raw.parent,0o700)
    files={};blobs={}
    for index,name in enumerate(acq.FILES):
        payload=f"fixture-{index}\n".encode();path=raw/name;path.write_bytes(payload);os.chmod(path,0o444)
        blob=hashlib.sha1(f"blob {len(payload)}\0".encode()+payload,usedforsecurity=False).hexdigest()
        blobs[name]=blob;files[name]={"sha256":acq.sha_bytes(payload),"size":len(payload),"git_blob_sha1":blob,"mode":0o444,"nlink":1}
    os.chmod(raw,0o555);raw_stat=raw.lstat()
    clone_dir="/tmp/msae-v5-acquire-fixture/repo";empty_home="/tmp/msae-v5-acquire-fixture/home"
    argvs=[[*config["ignore_argv"][:-1],"data/msae_independent_source_v5/raw/sentinel"],
           [*config["ignore_argv"][:-1],"data/msae_independent_source_v5/private/sentinel"],
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
    report={"schema_version":"msae_independent_source_v5_source_acquisition_v1","source_repo":acq.REPO,
        "source_commit":acq.COMMIT,"resolved_head":acq.COMMIT,"tree_object_sha1":tree,
        "tree_verified_from_ls_tree":True,"tree_paths":acq.FILES,"tree_blob_sha1":blobs,"files":files,
        "authority_manifest_sha256":manifest_sha,"authority_review_sha256":review_sha,
        "source_acquisition_entry_sha256":entry_sha,"acquisition_gate_argument":review_sha,
        "config_sha256":acq.sha_file(acq.CONFIG),"runner_sha256":acq.sha_file(ACQUISITION_SCRIPT),
        "executed_clone_argv":argvs[2],"executed_checkout_argv":argvs[3],
        "environment":{"GIT_CONFIG_NOSYSTEM":"1","GIT_TERMINAL_PROMPT":"0","HOME":empty_home,"PATH":"/usr/bin:/bin"},
        "clone_dir":clone_dir,"empty_home":empty_home,"proxy_variables_present":[],
        "ignore_checks":[{"path":"data/msae_independent_source_v5/raw/sentinel","stdout_sha256":by["ignore_raw"]["stdout_sha256"],
                          "stderr_sha256":by["ignore_raw"]["stderr_sha256"],"exit_status":0},
                         {"path":"data/msae_independent_source_v5/private/sentinel","stdout_sha256":by["ignore_private"]["stdout_sha256"],
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
        {"sent_id": "x!", "normalized": "x !"},
        {"sent_id": "\u00e9", "normalized": "e accent"},
    ]
    assigned = m.assign_split(rows)
    assert sorted(x["panel"] for x in assigned) == ["C1", "C2"]
    golden = {
        "schema_version": "msae_independent_source_v5_split_manifest_v1",
        "source_commit": "0" * 40,
        "split_algorithm": "sha256-canonical-json-array-v1-even-C1-odd-C2",
        "record_count": 2,
        "C1_count": 1,
        "C2_count": 1,
        "entries": [
            {"sent_id": "\u00e9", "panel": "C1", "zero_based_rank": 0, "split_key_sha256": "0" * 64},
            {"sent_id": "x!", "panel": "C2", "zero_based_rank": 1, "split_key_sha256": "f" * 64},
        ],
    }
    assert hashlib.sha256(m.canonical_file_bytes(golden)).hexdigest() == "1d131b624f72da60b576c173b16d91dba8d265eed701e27e8db0546ba2a1e513"
    assert m.split_key("x!", "x !") == hashlib.sha256(m.canonical_bytes(["msae-independent-source-v5/C1C2", "x!", "x !"])).hexdigest()


def test_create_once_private_payload_and_no_source_output(tmp_path: Path, capsys):
    private = tmp_path / "private"
    records = [{"canary": "MSAE_V5_SECRET_7f6b6aa8", "id": 1}]
    path = m.publish_private_jsonl(private, "payload.jsonl", records)
    assert path.stat().st_mode & 0o777 == 0o600
    assert private.stat().st_mode & 0o777 == 0o700
    assert capsys.readouterr() == ("", "")
    with pytest.raises(m.GateFailure, match="payload_already_exists"):
        m.publish_private_jsonl(private, "payload.jsonl", records)


def test_document_group_marker_is_terminal(tmp_path: Path):
    path = tmp_path / "grouped.conllu"
    path.write_bytes(b"# newdoc id = forbidden\n" + sample_conllu())
    with pytest.raises(m.GateFailure, match="unsupported_document_group"):
        m.parse_conllu(path)


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


def test_pedigree_normalization_git_equivalence_and_hash_domain():
    variants = [
        b"http://github.com/UniversalDependencies/UD_English-ParTUT.git/",
        b"https://github.com/universaldependencies/ud_english-partut.git",
        b"https://github.com/universaldependencies/ud_english-partut/",
    ]
    normalized = {m.normalize_pedigree(value) for value in variants}
    assert normalized == {"https://github.com/universaldependencies/ud_english-partut"}
    value = normalized.pop()
    assert m.pedigree_hash(value) == hashlib.sha256(b"msae-v5/pedigree\0" + value.encode()).hexdigest()


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
    assert snapshot["schema_version"] == "msae_independent_source_v5_process_snapshot_v1"
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


def test_inventory_rejects_populated_v5_and_directory_symlink_without_opening(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m,"ROOT",tmp_path)
    raw = tmp_path / "data/msae_independent_source_v5/raw"
    raw.mkdir(parents=True); secret = raw / "secret"; secret.write_text("must not open")
    with pytest.raises(m.GateFailure, match="preexisting_v5_namespace"):
        m.inventory_repository()
    secret.unlink(); raw.rmdir(); (tmp_path/"data/msae_independent_source_v5").rmdir()
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
    config=SCRIPT.parents[1]/"configs/msae_independent_source_v5/acquisition.json"
    value=m.validate_acquisition_config(config)
    assert value["required_runtime_input"] == "authority_review_sha256"


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


def test_authority_manifest_is_create_once_and_review_bound(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(m,"ROOT",tmp_path)
    prov=tmp_path/"reports/provenance/msae_independent_source_v5";prov.mkdir(parents=True)
    monkeypatch.setattr(m,"PROV",prov)
    required=[
        "docs/plan-msae-independent-source-v5.md",
        "reports/adversarial/msae_independent_source_v5_plan_review.md",
        "reports/provenance/msae_independent_source_v5/preacquisition_alias_screen.json",
        "reports/provenance/msae_independent_source_v5/historical_source_registry.json",
        "scripts/prepare_msae_independent_source_v5.py",
        "scripts/acquire_msae_independent_source_v5.py",
        "tests/test_prepare_msae_independent_source_v5.py",
        "configs/msae_independent_source_v5/acquisition.json",
        "reports/verification/msae_independent_source_v5_source_free_checks.log",
    ]
    for rel in required:
        path=tmp_path/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(rel)
    hashes={rel:m.sha_file(tmp_path/rel) for rel in required}
    impl=tmp_path/"reports/adversarial/msae_independent_source_v5_preacquisition_implementation_review.md"
    impl.write_text("VERDICT: SHIP\n"+"\n".join([*hashes.values(),m.sha_file(SCRIPT)]))
    entries=[]
    for path in sorted(item for item in tmp_path.rglob("*") if item.is_file()):
        st=path.lstat();rel=path.relative_to(tmp_path).as_posix()
        entries.append({"path":rel,"disposition":"v5_authority","size":st.st_size,"mode":st.st_mode&0o777,
                        "device":st.st_dev,"inode":st.st_ino,"nlink":st.st_nlink,"mtime_ns":st.st_mtime_ns,
                        "sha256":m.sha_file(path)})
    baseline={"entries":entries,"entries_sha256":m.sha_bytes(m.canonical_bytes(entries)),"training_root_entries":[],
              "training_root_entries_sha256":m.sha_bytes(m.canonical_bytes([])),"quarantine_content_reads":0,
              "process_snapshot":{"status":"eligible","forbidden_identity_count":0}}
    m.write_json(prov/"baseline_inventory.json",baseline)
    m.build_authority_manifest()
    with pytest.raises(m.GateFailure,match="authority_manifest_already_exists"):
        m.build_authority_manifest()
    review=tmp_path/"reports/adversarial/msae_independent_source_v5_preacquisition_authority_review.md"
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
    monkeypatch.setattr(m,"ROOT",tmp_path);prov=tmp_path/"reports/provenance/msae_independent_source_v5";prov.mkdir(parents=True)
    monkeypatch.setattr(m,"PROV",prov)
    paths=["docs/plan-msae-independent-source-v5.md","reports/adversarial/msae_independent_source_v5_plan_review.md",
           "reports/provenance/msae_independent_source_v5/preacquisition_alias_screen.json",
           "reports/provenance/msae_independent_source_v5/historical_source_registry.json","tests/test_prepare_msae_independent_source_v5.py",
           "configs/msae_independent_source_v5/acquisition.json","reports/verification/msae_independent_source_v5_source_free_checks.log",
           "scripts/acquire_msae_independent_source_v5.py"]
    for rel in paths:
        path=tmp_path/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(rel)
    review=tmp_path/"reports/adversarial/msae_independent_source_v5_preacquisition_implementation_review.md"
    review.write_text("VERDICT: BLOCK\n")
    monkeypatch.setattr(m,"validate_acquisition_config",lambda _path:{})
    with pytest.raises(m.GateFailure,match="review_binding_ineligible"):
        m.build_baseline()
    assert not (prov/"baseline_inventory.json").exists()


def test_overlength_candidate_pedigree_field_is_terminal(tmp_path: Path, monkeypatch):
    raw=tmp_path/"raw";raw.mkdir();(raw/"README.md").write_bytes(b'{"dataset":"'+b"x"*1025+b'"}')
    (raw/"LICENSE.txt").write_text("license")
    prov=tmp_path/"prov";prov.mkdir();m.write_json(prov/"historical_source_registry.json",{"entries":[],"allowed_framework_identifiers":[]})
    monkeypatch.setattr(m,"RAW",raw);monkeypatch.setattr(m,"PROV",prov)
    with pytest.raises(m.GateFailure,match="ambiguous_candidate_pedigree_syntax"):
        m.candidate_pedigree()


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
    ("unlink","blocked"),("final_check","blocked"),("parent_fsync","blocked")))
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
    state="blocked" if path.exists() or temp.exists() else "absent"
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
        "scripts/acquire_msae_independent_source_v5.py":acq.sha_file(ACQUISITION_SCRIPT),
        "configs/msae_independent_source_v5/acquisition.json":acq.sha_file(config)}}))
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
    raw=tmp_path/"data/msae_independent_source_v5/raw"/acq.COMMIT
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
    raw=tmp_path/"data/msae_independent_source_v5/raw"/m.COMMIT;raw.mkdir(parents=True)
    monkeypatch.setattr(m,"RAW",raw)
    os.chmod(raw.parent.parent,0o700);os.chmod(raw.parent,0o700);os.chmod(raw,0o555)
    for name in [*m.SOURCE_FILES.values(),"README.md","LICENSE.txt"]:
        path=raw/name;path.write_text("x");os.chmod(path,0o444)
    monkeypatch.setattr(m,"RAW",raw)
    m.verify_pre_payload_v5_namespace()
    if mutation=="private_file":
        private=raw.parent.parent/"private";private.mkdir();(private/"unexpected.txt").write_text("x")
        code="v5_namespace_extra_path"
    else:
        os.chmod(raw,0o755);extra=raw/"extra.txt"
        if mutation=="extra_file":extra.write_text("x")
        elif mutation=="file_symlink":extra.symlink_to(raw/"README.md")
        else:os.link(raw/"README.md",extra)
        os.chmod(raw,0o555);code="raw_file_set_drift"
    with pytest.raises(m.GateFailure,match=code):
        m.verify_pre_payload_v5_namespace()


def test_lexical_support_is_hashed():
    value = "MSAE_V5_SECRET_LEMMA_9d3e"
    item = m.public_label("lemma_identity", value)
    assert value not in json.dumps(item)
    assert item == hashlib.sha256(("msae-v5/lemma\0" + value).encode()).hexdigest()


def test_quarantine_inventory_is_lstat_only(tmp_path: Path, monkeypatch):
    q = tmp_path / "q.jsonl"
    q.write_text("MSAE_V5_MUST_NOT_OPEN")
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


def test_verify_terminal_rejection_enforces_payload_absence(tmp_path: Path, monkeypatch):
    prov=tmp_path/"reports/provenance/msae_independent_source_v5";prov.mkdir(parents=True)
    private=tmp_path/"data/msae_independent_source_v5/private";private.mkdir(parents=True)
    monkeypatch.setattr(m,"ROOT",tmp_path);monkeypatch.setattr(m,"PROV",prov);monkeypatch.setattr(m,"PRIVATE",private)
    rejection={"schema_version":"msae_independent_source_v5_rejection_v1","status":"rejected",
        "failure_code":"fixture","payload_created":False,"payload":None,"source_content_reported":False,
        "model_operations_initiated_by_builder":0,"gpu_queries_initiated_by_builder":0,"training_runs_initiated_by_builder":0,
        "model_scoring_authorized":False,"k2_or_branch_training_authorized":False,"stage_c_authorized":False,
        "terminal_process_snapshot":m.process_snapshot(),"training_root_status":"unchanged",
        "next_action":"new_reviewed_protocol_only",
        "scientific_artifact_inventory":m.scientific_artifact_inventory(),"payload_state":m.payload_state()}
    m.write_json(prov/"rejection.json",rejection);m.verify_terminal()
    rejection["payload_created"]=True
    (prov/"rejection.json").write_bytes(m.canonical_file_bytes(rejection))
    with pytest.raises(m.GateFailure,match="rejection_verification"):m.verify_terminal()
    rejection["payload_created"]=False
    (prov/"rejection.json").write_bytes(m.canonical_file_bytes(rejection))
    (private/"blind_payload.jsonl").write_text("unexpected")
    with pytest.raises(m.GateFailure,match="rejection_payload_state_drift"):
        m.verify_terminal()


def test_rejection_binds_public_and_private_abandoned_temporaries(tmp_path: Path, monkeypatch):
    prov=tmp_path/"reports/provenance/msae_independent_source_v5";prov.mkdir(parents=True)
    private=tmp_path/"data/msae_independent_source_v5/private";private.mkdir(parents=True)
    public_temp=prov/".support.json.building";public_temp.write_text("partial-public")
    private_temp=private/".blind_payload.jsonl.building";private_temp.write_text("must-not-open")
    monkeypatch.setattr(m,"ROOT",tmp_path);monkeypatch.setattr(m,"PROV",prov);monkeypatch.setattr(m,"PRIVATE",private)
    snapshot=m.process_snapshot();monkeypatch.setattr(m,"process_snapshot",lambda:snapshot)
    real_open=Path.open
    def guarded_open(self,*args,**kwargs):
        if self==private_temp:raise AssertionError("private temporary opened")
        return real_open(self,*args,**kwargs)
    monkeypatch.setattr(Path,"open",guarded_open)
    m.retain_rejection("abandoned_payload_temporary");m.verify_terminal()
    public_temp.write_text("mutated-public")
    with pytest.raises(m.GateFailure,match="rejection_artifact_inventory_drift"):
        m.verify_terminal()


def test_verify_terminal_complete_synthetic_success(tmp_path: Path, monkeypatch):
    prov=tmp_path/"reports/provenance/msae_independent_source_v5";prov.mkdir(parents=True)
    private=tmp_path/"data/msae_independent_source_v5/private";private.mkdir(parents=True)
    os.chmod(private,0o700)
    monkeypatch.setattr(m,"ROOT",tmp_path);monkeypatch.setattr(m,"PROV",prov);monkeypatch.setattr(m,"PRIVATE",private)
    for rel in ("docs/plan-msae-independent-source-v5.md","reports/adversarial/msae_independent_source_v5_plan_review.md",
                "scripts/acquire_msae_independent_source_v5.py","tests/test_prepare_msae_independent_source_v5.py"):
        path=tmp_path/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(rel)
    h="a"*64
    split={"schema_version":"msae_independent_source_v5_split_manifest_v1","source_commit":m.COMMIT,
           "upstream_partition":"test","split_algorithm":"sha256-canonical-json-array-v1-even-C1-odd-C2",
           "record_count":2,"C1_count":1,"C2_count":1,
           "entries":[{"sent_id":"a","panel":"C1","zero_based_rank":0,"split_key_sha256":h,"source_record_sha256":h},
                      {"sent_id":"b","panel":"C2","zero_based_rank":1,"split_key_sha256":h,"source_record_sha256":h}]}
    roles={"schema_version":"msae_independent_source_v5_role_manifest_v1","source_commit":m.COMMIT,"roles":{
        "discovery":{"upstream_partition":"train","record_count":1,
                     "entries":[{"zero_based_rank":0,"sent_id":"d","source_record_sha256":h}]},
        "calibration":{"upstream_partition":"dev","record_count":1,
                       "entries":[{"zero_based_rank":0,"sent_id":"c","source_record_sha256":h}]}}}
    partition=lambda sentences:{"integer_tokens":sentences,"multiword_rows":0,"empty_node_rows":0,
                                "sentences":sentences,"sha256":h}
    source={"schema_version":"msae_independent_source_v5_source_manifest_v1","source_commit":m.COMMIT,
            "source_text_published":False,"partitions":{"train":partition(1),"dev":partition(1),"test":partition(2)}}
    dedup_role=lambda upstream,count:{"upstream_partition":upstream,"input_count":count,"retained_count":count,
        "within_partition_dropped_count":0,"within_partition_dropped_ids_sha256":h,
        "cross_partition_dropped_count":0,"cross_partition_dropped_ids_sha256":h}
    dedup={"schema_version":"msae_independent_source_v5_dedup_v1","roles":{
        "discovery":dedup_role("train",1),"calibration":dedup_role("dev",1),"test":dedup_role("test",2)},
        "cross_partition_normalized_group_count":0,"source_text_published":False}
    task_record={"eligible":True,"retained_class_count":2,"distinct_utterances_by_class":{"a":20,"b":20}}
    support_role=lambda count:{"utterance_count":count,"tasks":{task:dict(task_record) for task in m.TASKS}}
    support={"schema_version":"msae_independent_source_v5_support_v1","floor_distinct_utterances":20,
        "status":"eligible","roles":{"discovery":support_role(1),"calibration":support_role(1),
                                        "C1":support_role(1),"C2":support_role(1)},
        "all_role_task_intersection":sorted(m.TASKS),
        "unsupported_tasks":["neutral_prefix_offset","entity_binary","entity_type","source_genre"]}
    snapshot={"schema_version":"msae_independent_source_v5_process_snapshot_v1",
        "observation_scope":"point_in_time_proc_snapshot","forbidden_tokens":list(m.FORBIDDEN_PROCESS_TOKENS),
        "process_count":0,"entries":[],"forbidden_identity_count":0,"status":"eligible"}
    baseline={"schema_version":"msae_independent_source_v5_baseline_inventory_v1",
        "baseline_head":"7e1a6fc7a26a870a4edcf29c96b7cdf3cdbd7faa","entry_count":0,"counts":{},
        "quarantine_content_reads":0,"entries":[],"authority_expected_absent":[],
        "entries_sha256":m.sha_bytes(m.canonical_bytes([])),"status":"eligible","process_snapshot":snapshot,
        "training_root_entries":[],"training_root_entries_sha256":m.sha_bytes(m.canonical_bytes([]))}
    raw=tmp_path/"data/msae_independent_source_v5/raw"/m.COMMIT;raw.mkdir(parents=True)
    monkeypatch.setattr(m,"RAW",raw)
    (raw/"LICENSE.txt").write_text("fixture license",encoding="utf-8");(raw/"README.md").write_text("fixture readme",encoding="utf-8")
    census={"schema_version":"msae_independent_source_v5_document_group_census_v1","newdoc_marker_count":0,
        "markers_by_file":{name:0 for name in m.SOURCE_FILES.values()},"natural_unit":"sentence",
        "document_speaker_cluster_inference_authorized":False,"status":"eligible"}
    license_value={"schema_version":"msae_independent_source_v5_license_v1","license_id":"CC-BY-SA-4.0",
        "license_path":"LICENSE.txt","license_sha256":m.sha_file(raw/"LICENSE.txt"),
        "readme_sha256":m.sha_file(raw/"README.md"),"license_url":"https://creativecommons.org/licenses/by-sa/4.0/",
        "obligations":["attribution","share_alike"],"raw_committed":False,"payload_committed":False,
        "contradiction_count":0,"status":"eligible"}
    family={"schema_version":"msae_independent_source_v5_source_family_v1","status":"eligible",
        "disposition":"previously_considered_but_project_source_use_unseen","planning_or_authority_matches":[],
        "unexpected_matches":[],"pathname_matches":[],"unexpected_pathname_matches":[],
        "bound_planning_occurrences_exact":True,"whole_file_digest_matches":[]}
    registry={"schema_version":"msae_independent_source_v5_historical_source_registry_v1"}
    pedigree={"schema_version":"msae_independent_source_v5_candidate_pedigree_v1",
        "registry_sha256":"PLACEHOLDER","candidate_identifier_count":1,"candidate_identifier_sha256":[h],
        "allowed_shared_identifier_sha256":[],"blocking_identifier_sha256":[],"blocking_identifier_count":0,
        "source_prose_published":False,"status":"eligible"}
    values={
        "baseline_inventory.json":baseline,
        "source_acquisition_entry.json":{"schema_version":"msae_independent_source_v5_source_acquisition_entry_v1"},
        "source_acquisition.json":{"schema_version":"msae_independent_source_v5_source_acquisition_v1"},
        "source_family.json":family,"candidate_pedigree.json":pedigree,
        "license.json":license_value,"document_group_census.json":census,
        "source_manifest.json":source,"dedup.json":dedup,
        "history_manifest.json":baseline,
        "history_overlap.json":{"schema_version":"msae_independent_source_v5_history_overlap_v1",
            "baseline_inventory_sha256":"PLACEHOLDER","history_entries_sha256":baseline["entries_sha256"],
            "history_unit_count":0,"history_adapter_census":{},"candidate_utterance_count":4,
            "blocking_collision_count":0,"blocking_collisions":[],"quarantine_content_reads":0,
            "opaque_binary_history_count":0,"status":"eligible"},
        "cross_role_overlap.json":{"schema_version":"msae_independent_source_v5_cross_role_overlap_v1",
            "blocking_collision_count":0,"blocking_collisions":[],"status":"eligible"},
        "support.json":support,"role_manifest.json":roles,"split_manifest.json":split,
        "post_process_snapshot.json":snapshot,
        "preacquisition_alias_screen.json":{"schema_version":"msae_independent_source_v5_preacquisition_alias_screen_v2"},
        "historical_source_registry.json":{"schema_version":"msae_independent_source_v5_historical_source_registry_v1"},
        "preacquisition_authority_manifest.json":{"schema_version":"msae_independent_source_v5_preacquisition_authority_v1"},
    }
    values["historical_source_registry.json"]=registry
    # Cross-file hashes are filled only after their canonical upstream values exist.
    for name,value in values.items():
        if name not in {"candidate_pedigree.json","history_overlap.json"}:m.write_json(prov/name,value)
    pedigree["registry_sha256"]=m.sha_file(prov/"historical_source_registry.json")
    values["history_overlap.json"]["baseline_inventory_sha256"]=m.sha_file(prov/"baseline_inventory.json")
    m.write_json(prov/"candidate_pedigree.json",pedigree);m.write_json(prov/"history_overlap.json",values["history_overlap.json"])
    payload=private/"blind_payload.jsonl";payload.write_bytes(b"opaque\n");os.chmod(payload,0o600);ps=payload.lstat()
    bindings={name:m.sha_file(prov/name) for name in values}
    seal={"schema_version":"msae_independent_source_v5_seal_v1",
          "status":"independent_source_ready_for_future_prescore_protocol",
          "source_status":"previously_considered_but_project_source_use_unseen",
          "plan_sha256":m.sha_file(tmp_path/"docs/plan-msae-independent-source-v5.md"),
          "plan_review_sha256":m.sha_file(tmp_path/"reports/adversarial/msae_independent_source_v5_plan_review.md"),
          "program_sha256":m.sha_file(SCRIPT),
          "acquisition_runner_sha256":m.sha_file(tmp_path/"scripts/acquire_msae_independent_source_v5.py"),
          "test_sha256":m.sha_file(tmp_path/"tests/test_prepare_msae_independent_source_v5.py"),
          "artifact_sha256":bindings,
          "payload":{"path":"data/msae_independent_source_v5/private/blind_payload.jsonl",
                     "sha256":m.sha_file(payload),"size":ps.st_size,"record_count":2,"mode":0o600,"nlink":1},
          "model_operations_initiated_by_builder":0,"gpu_queries_initiated_by_builder":0,
          "training_runs_initiated_by_builder":0,
          "external_observation_scope":"baseline_and_terminal_proc_snapshots_plus_training_root_diff",
          "unsupported_tasks":["neutral_prefix_offset","entity_binary","entity_type","source_genre"],
          "opaque_binary_history_excluded":True,"document_speaker_cluster_inference_authorized":False}
    seal_sha=m.sha_bytes(m.canonical_file_bytes(seal))
    m.write_json(prov/"no_training_gate.json",{"schema_version":"msae_independent_source_v5_no_training_gate_v1","status":"pending_terminal_seal",
        "terminal_status_if_seal_matches":seal["status"],"seal_sha256":seal_sha,
        "model_scoring_authorized":False,"k2_or_branch_training_authorized":False,"stage_c_authorized":False})
    m.write_json(prov/"seal.json",seal)
    monkeypatch.setattr(m,"_verify_predecessor_and_raw",lambda:{})
    monkeypatch.setattr(m,"reconstruct_scientific_artifacts",lambda:{"sha256":m.sha_file(payload),"size":ps.st_size,"record_count":2})
    m.verify_terminal()
    (prov/"seal.json").write_text(json.dumps(seal,indent=2),encoding="utf-8")
    with pytest.raises(m.GateFailure,match="noncanonical_public_json"):m.verify_terminal()
    (prov/"seal.json").write_bytes(m.canonical_file_bytes(seal))
    bad_snapshot=dict(snapshot);bad_snapshot["forbidden_identity_count"]=1
    (prov/"post_process_snapshot.json").write_bytes(m.canonical_file_bytes(bad_snapshot))
    with pytest.raises(m.GateFailure,match="scientific_artifact_reconstruction"):m.validate_scientific_artifacts()
    (prov/"post_process_snapshot.json").write_bytes(m.canonical_file_bytes(snapshot))
    seal["model_operations_initiated_by_builder"]=1
    (prov/"seal.json").write_bytes(m.canonical_file_bytes(seal))
    with pytest.raises(m.GateFailure,match="seal_verification"):m.verify_terminal()
