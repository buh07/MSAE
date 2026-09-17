from __future__ import annotations

import hashlib
import io
import json
import stat
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_msae_independent_norspan_v1 as n  # noqa: E402


def conllu(*, with_group: bool = True, group: str = "doc-1", sent_id: str = "s1") -> str:
    lines = []
    if with_group:
        lines.append(f"# newdoc id = {group}")
    lines.extend([
        f"# sent_id = {sent_id}",
        "1\tDette\tdette\tPRON\t_\tNumber=Sing\t2\tnsubj\t_\t_",
        "2\ter\tvære\tAUX\t_\t_\t0\troot\t_\t_",
        "3\ttest\ttest\tNOUN\t_\tNumber=Sing\t2\tobj\t_\t_",
        "4\t.\t.\tPUNCT\t_\t_\t2\tpunct\t_\t_",
        "",
    ])
    return "\n".join(lines)


@pytest.mark.parametrize(
    ("group", "role", "digest", "value"),
    [
        (("train", "doc-0"), "discovery", "16e0447098358da636236389dbe7f00a015bd3a39919ccdd579df1888b7344de", 1648392713998273958),
        (("train", "doc-2"), "calibration", "c1cfc78bbdcd68e0dcc4d80d0a30567559c4995250f42cc56861f1f12ddce013", 13965600372497934560),
        (("train", "doc-7"), "C1", "e3adef2ce9f161f82467f2037cb514a6786249c6e9e4cda27e8e149fdbf6e28e", 16406031993763095032),
        (("train", "doc-20"), "C2", "fe379fa55a3e9847f70c9b18cc0eca7be681a65ec96b4d6c58a964f27c39ddbc", 18318285541885253703),
    ],
)
def test_role_goldens(group, role, digest, value):
    assert n.role_for_group(group) == (role, digest, value)


@pytest.mark.parametrize(
    ("text", "status"),
    [
        ("CC BY-SA 4.0", "eligible"),
        ("https://creativecommons.org/licenses/by-sa/4.0\n", "eligible"),
        ("two https://creativecommons.org/licenses/by-sa/4.0 and https://creativecommons.org/licenses/by-sa/4.0/\n", "eligible"),
        ("xhttps://creativecommons.org/licenses/by-sa/4.0x", "ineligible"),
        ("CC BY-SA 4.0 and GPL-3.0", "ineligible"),
        ("GPL-3.0", "ineligible"),
        ("MIT", "ineligible"),
        ("CC-BY-SA-4.0ish", "ineligible"),
        ("all rights reserved CC BY-SA 4.0", "ineligible"),
        ("", "ineligible"),
    ],
)
def test_license_goldens(text, status):
    assert n.license_evidence(text)["status"] == status


def test_parse_requires_document_group(tmp_path):
    path = tmp_path / "x.conllu"
    path.write_text(conllu(with_group=False), "utf-8")
    with pytest.raises(n.GateFailure, match="missing_document_group"):
        n.parse_conllu(path, "train")


def test_parse_group_and_labels(tmp_path):
    path = tmp_path / "x.conllu"
    path.write_text(conllu(), "utf-8")
    sentences, counts = n.parse_conllu(path, "train")
    assert counts["sentences"] == 1
    assert counts["document_groups"] == 1
    assert sentences[0].group_key == ("train", "doc-1")
    labels = n.sentence_labels(sentences[0])
    assert labels[0]["absolute_bucket"] == "0"
    assert labels[0]["number"] == "Sing"
    assert labels[1]["head_signed_distance"] == "ROOT"


def test_parse_rejects_unknown_number(tmp_path):
    path = tmp_path / "x.conllu"
    path.write_text(conllu().replace("Number=Sing", "Number=Other", 1), "utf-8")
    with pytest.raises(n.GateFailure, match="unknown_number"):
        n.parse_conllu(path, "train")


def test_overlap_predicate():
    assert n.overlap_reason(("a", "b"), ("x", "a", "b", "y")) == "contained_short"
    assert n.overlap_reason(("a", "b"), ("a", "b")) == "exact"
    assert n.overlap_reason(("a",), ("b",)) is None


def test_internal_prune_is_deterministic(tmp_path):
    p1 = tmp_path / "one.conllu"
    p2 = tmp_path / "two.conllu"
    p1.write_text(conllu(group="a", sent_id="s1"), "utf-8")
    p2.write_text(conllu(group="b", sent_id="s2"), "utf-8")
    one = n.parse_conllu(p1, "train")[0][0]
    two = n.parse_conllu(p2, "dev")[0][0]
    kept_a, report_a = n.internal_prune([one, two])
    kept_b, report_b = n.internal_prune([two, one])
    assert kept_a == kept_b
    assert report_a == report_b
    assert len(kept_a) == 1


def test_cross_role_detects_collision(tmp_path):
    p1 = tmp_path / "one.conllu"
    p2 = tmp_path / "two.conllu"
    p1.write_text(conllu(group="a", sent_id="s1"), "utf-8")
    p2.write_text(conllu(group="b", sent_id="s2"), "utf-8")
    one = n.parse_conllu(p1, "train")[0][0]
    two = n.parse_conllu(p2, "dev")[0][0]
    roles = {"discovery": [one], "calibration": [two], "C1": [], "C2": []}
    assert n.cross_role_overlap(roles)["status"] == "ineligible"


def test_dedup_keeps_lexicographic_partition(tmp_path):
    paths = []
    for partition, group, sent in (("train", "a", "s1"), ("dev", "b", "s2")):
        path = tmp_path / f"{partition}.conllu"
        path.write_text(conllu(group=group, sent_id=sent), "utf-8")
        paths.append((partition, path))
    rows = [n.parse_conllu(path, partition)[0][0] for partition, path in paths]
    kept, report = n.deduplicate(rows)
    assert kept[0].partition == "dev"
    assert report["dropped_count"] == 1


def test_archive_rejects_nested(tmp_path):
    path = tmp_path / "x.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("nested.tar", b"x")
    cfg = n.load_config()
    with pytest.raises(n.GateFailure, match="nested_archive"):
        list(n._archive_text_members(path, cfg))


def test_archive_rejects_traversal(tmp_path):
    path = tmp_path / "x.tar"
    with tarfile.open(path, "w") as archive:
        data = b"text"
        info = tarfile.TarInfo("../bad.txt")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    cfg = n.load_config()
    with pytest.raises(n.GateFailure, match="unsafe_archive_member"):
        list(n._archive_text_members(path, cfg))


def test_identity_hash_domains():
    assert n.public_label("token_identity", "x") == hashlib.sha256(b"norspan-1/token\0x").hexdigest()
    assert n.public_label("lemma_identity", "x") == hashlib.sha256(b"norspan-1/lemma\0x").hexdigest()


def test_config_runtime_and_authority():
    cfg = n.load_config()
    assert cfg["protocol_id"] == "NORSPAN-1"
    assert cfg["authorizations"] == {
        "model_scoring": False,
        "gpu_query": False,
        "k2_or_branch_training": False,
        "stage_c": False,
    }


def test_license_raw_utf8_nul_and_repeated_occurrences():
    assert n.license_evidence(b"\xff")["status"] == "ineligible"
    assert n.license_evidence(b"CC BY-SA 4.0\0")["status"] == "ineligible"
    report = n.license_evidence(b"CC BY-SA 4.0 and CC BY-SA 4.0")
    assert report["status"] == "eligible"
    assert report["accepted_phrase_count"] == 2


def test_identity_labels_use_nfkc_casefold(tmp_path):
    path = tmp_path / "x.conllu"
    path.write_text(conllu().replace("Dette", "\uff2b"), "utf-8")
    sentence = n.parse_conllu(path, "train")[0][0]
    assert n.sentence_labels(sentence)[0]["token_identity"] == "k"


@pytest.mark.parametrize(
    ("section", "key", "value", "code"),
    [
        ("source", "repo", "https://invalid.example/x", "config_source"),
        ("runtime", "unicode", "0.0.0", "unicode_version"),
        ("license", "max_bytes", 3, "config_license"),
        ("pedigree", "domain_hex", "00", "config_pedigree_domain"),
        ("role", "domain", "wrong", "config_role"),
        ("support", "distinct_sentence_floor", 19, "config_support"),
        ("overlap", "short_max_tokens", 8, "config_overlap"),
        ("history", "archive_max_members", 1, "config_history"),
        ("authorizations", "gpu_query", True, "config_authorizations"),
        ("acquisition_limits", "command_timeout_seconds", 601, "config_acquisition_limits"),
        ("acquisition_limits", "stdout_limit_bytes", 16777216.0, "config_acquisition_limits"),
    ],
)
def test_config_single_field_mutations_fail(tmp_path, monkeypatch, section, key, value, code):
    cfg = json.loads(n.CONFIG_PATH.read_text("utf-8"))
    cfg[section][key] = value
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(cfg), "utf-8")
    monkeypatch.setattr(n, "CONFIG_PATH", path)
    with pytest.raises(n.GateFailure, match=code):
        n.load_config()


def test_history_walker_records_protected_without_read(tmp_path, monkeypatch):
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "secret.txt").write_text("must not read", "utf-8")
    (tmp_path / "public.txt").write_text("public", "utf-8")
    (tmp_path / "weights.pt").write_bytes(b"private-model")
    monkeypatch.setattr(n, "ROOT", tmp_path)
    rows = list(n._history_objects())
    by_path = {rel: disposition for rel, _, _, disposition in rows}
    assert by_path["private"] == "protected_directory_lstat_only"
    assert "private/secret.txt" not in by_path
    assert by_path["weights.pt"] == "candidate_regular"
    assert n.classify_file(tmp_path / "weights.pt") == "binary_excluded"


def test_archive_requires_supported_magic(tmp_path):
    path = tmp_path / "fake.zip"
    path.write_bytes(b"not a zip")
    with pytest.raises(n.GateFailure, match="unsupported_archive_magic"):
        n.classify_file(path)


def test_archive_declared_member_limit(tmp_path):
    path = tmp_path / "large.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("large.txt", b"1234")
    cfg = n.load_config()
    cfg = json.loads(json.dumps(cfg))
    cfg["history"]["archive_max_member_bytes"] = 3
    with pytest.raises(n.GateFailure, match="archive_limit"):
        list(n._archive_text_members(path, cfg))


def _set_protocol_root(monkeypatch, root):
    monkeypatch.setattr(n, "ROOT", root)
    monkeypatch.setattr(n, "PROV", root / "reports/provenance/msae_independent_norspan_v1")
    monkeypatch.setattr(n, "DATA", root / "data/msae_independent_norspan_v1")
    monkeypatch.setattr(n, "RAW", n.DATA / "raw" / n.COMMIT)
    monkeypatch.setattr(n, "PRIVATE", n.DATA / "private")


def test_state_classifier_baseline_and_extra(tmp_path, monkeypatch):
    _set_protocol_root(monkeypatch, tmp_path)
    assert n.classify_protocol_state() == "clean_reviewed"
    n.PROV.mkdir(parents=True)
    n.PROV.chmod(0o755)
    for name in ("current_history_registry.json", "baseline.json"):
        (n.PROV / name).write_text("{}\n", "utf-8")
        (n.PROV / name).chmod(0o644)
    assert n.classify_protocol_state() == "baseline"
    (n.PROV / "unexpected.json").write_text("{}\n", "utf-8")
    with pytest.raises(n.GateFailure, match="protocol_extra_public"):
        n.classify_protocol_state()


def test_state_classifier_all_preterminal_rows(tmp_path, monkeypatch):
    _set_protocol_root(monkeypatch, tmp_path)
    n.PROV.mkdir(parents=True)
    n.PROV.chmod(0o755)
    for name in ("current_history_registry.json", "baseline.json"):
        (n.PROV / name).write_text("{}\n", "utf-8")
        (n.PROV / name).chmod(0o644)
    (n.PROV / "authority.json").write_text("{}\n", "utf-8")
    (n.PROV / "authority.json").chmod(0o644)
    review = tmp_path / "reports/adversarial/msae_independent_norspan_v1_authority_review.md"
    review.parent.mkdir(parents=True)
    review.write_text("VERDICT: SHIP\n", "utf-8")
    assert n.classify_protocol_state() == "authority"
    expected = [
        ("acquisition_entry.json", "acquisition_entered"),
        ("pre_network_ready.json", "network_ready"),
        ("network_started.json", "network_started"),
    ]
    for filename, state in expected:
        (n.PROV / filename).write_text("{}\n", "utf-8")
        (n.PROV / filename).chmod(0o644)
        assert n.classify_protocol_state() == state


def test_publication_is_create_once_and_nofollow(tmp_path):
    target = tmp_path / "a" / "value.json"
    n.publish_bytes(target, b"x", 0o640)
    st = target.lstat()
    assert stat.S_IMODE(st.st_mode) == 0o640
    assert st.st_nlink == 1
    with pytest.raises(n.GateFailure, match="create_once_exists"):
        n.publish_bytes(target, b"y", 0o640)


def test_flat_directory_publication(tmp_path):
    target = tmp_path / "raw" / "commit"
    n.ensure_directory(target.parent, 0o700)
    manifest = n.publish_flat_directory(target, {"a": b"one", "b": b"two"},
                                        directory_mode=0o555, file_mode=0o444)
    assert set(p.name for p in target.iterdir()) == {"a", "b"}
    assert manifest["a"]["sha256"] == hashlib.sha256(b"one").hexdigest()
    assert stat.S_IMODE((target / "a").stat().st_mode) == 0o444


def test_evidence_compatibility_rejects_training_and_porcelain_drift():
    base = {"training": {"entry_count": 0, "manifest_sha256": "a"},
            "porcelain": {"outside_protocol_count": 0, "outside_protocol_sha256": "b"}}
    current = {"training": dict(base["training"]), "porcelain": dict(base["porcelain"]),
               "process": {"prohibited_match_count": 0}}
    n.evidence_compatible(base, current)
    current["training"]["entry_count"] = 1
    with pytest.raises(n.GateFailure, match="training_state_drift"):
        n.evidence_compatible(base, current)


def test_acquisition_tree_parser_and_sparse_reader(tmp_path):
    import acquire_msae_independent_norspan_v1 as a
    rows = []
    for index, name in enumerate(a.FILES):
        rows.append(f"100644 blob {index:040x}\t{name}".encode())
    digest, blobs = a.parse_tree(b"\0".join(rows) + b"\0")
    assert len(digest) == 64 and list(blobs) == a.FILES
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    for name in a.FILES:
        (repo / name).write_bytes(name.encode())
    payloads = a.read_sparse_files(repo)
    assert list(payloads) == a.FILES
    (repo / "extra.txt").write_text("x", "utf-8")
    with pytest.raises(n.GateFailure, match="sparse_worktree_cardinality"):
        a.read_sparse_files(repo)


def test_acquisition_runner_orders_sparse_before_checkout():
    import inspect
    import acquire_msae_independent_norspan_v1 as a
    source = inspect.getsource(a.acquire)
    assert source.index('(\"sparse_init\"') < source.index('(\"checkout\"')
    assert source.index('(\"sparse_set\"') < source.index('(\"checkout\"')
    assert "ignore_errors=True" not in source


def _registry_entry(path, adapter, extracted=0, digest=None):
    st = path.lstat()
    return {"path": path.name, "device": st.st_dev, "inode": st.st_ino,
            "type": stat.S_IFMT(st.st_mode), "mode": stat.S_IMODE(st.st_mode),
            "nlink": st.st_nlink, "size": st.st_size, "sha256": digest,
            "adapter": adapter, "extracted_unit_count": extracted}


def test_mixed_history_registry_skips_lstat_only(tmp_path, monkeypatch):
    cfg = n.load_config()
    protected = tmp_path / "private"
    protected.mkdir()
    public = tmp_path / "public.txt"
    public.write_text("unrelated historical text\n", "utf-8")
    source = tmp_path / "source.conllu"
    source.write_text(conllu(), "utf-8")
    sentence = n.parse_conllu(source, "train")[0][0]
    p = _registry_entry(protected, "protected_directory_lstat_only")
    t = _registry_entry(public, "text", extracted=1, digest=n.sha_file(public))
    p["path"] = "private"; t["path"] = "public.txt"
    registry = {"entries": [p, t]}
    monkeypatch.setattr(n, "ROOT", tmp_path)
    implicated, report = n.history_collisions([sentence], registry, cfg)
    assert implicated == set()
    assert report["history_unit_count"] == 1


def test_quarantine_paths_receive_exact_lstat_records(tmp_path, monkeypatch):
    private = tmp_path / "data/atlas_v1/private"
    private.mkdir(parents=True)
    for name in ("final.jsonl", "final.records.jsonl", "final.units.jsonl"):
        (private / name).write_bytes(b"do-not-read")
    monkeypatch.setattr(n, "ROOT", tmp_path)
    rows = {rel: disposition for rel, _, _, disposition in n._history_objects()}
    for rel in n.QUARANTINES:
        assert rows[rel] == "quarantine_file_lstat_only"


def test_archive_directory_members_count_toward_limit(tmp_path):
    path = tmp_path / "directories.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("one/", b"")
        archive.writestr("two/", b"")
    cfg = json.loads(json.dumps(n.load_config()))
    cfg["history"]["archive_max_members"] = 1
    with pytest.raises(n.GateFailure, match="archive_limit"):
        list(n._archive_text_members(path, cfg))


def test_group_normalization_rejects_nfkc_introduced_boundary_space():
    with pytest.raises(n.GateFailure, match="invalid_document_group_whitespace"):
        n._normalize_doc_id("\u00a8doc")
    assert n._normalize_doc_id("  DOC\t") == "doc"


def test_state_classifier_rejects_unexpected_empty_data_directory(tmp_path, monkeypatch):
    _set_protocol_root(monkeypatch, tmp_path)
    n.DATA.mkdir(parents=True)
    n.DATA.chmod(0o700)
    (n.DATA / "unexpected-empty").mkdir()
    with pytest.raises(n.GateFailure, match="protocol_extra_data"):
        n.classify_protocol_state()


def test_review_ship_must_be_canonical_first_line(tmp_path):
    path = tmp_path / "review.md"
    path.write_text("VERDICT: BLOCK\nquoted VERDICT: SHIP\n", "utf-8")
    path.chmod(0o644)
    assert not n.review_is_ship(path)
    path.write_text("VERDICT: SHIP\n", "utf-8")
    path.chmod(0o644)
    assert n.review_is_ship(path)


def test_full_pedigree_identifier_universe_is_bound():
    cfg = n.load_config()
    identifiers = {tuple(row) for row in cfg["pedigree"]["identifiers"]}
    assert ("https", "github", "com", "universaldependencies", "ud", "norwegian", "bokmaal") in identifiers
    assert ("https", "github", "com", "universaldependencies", "ud", "norwegian", "bokmaal", "git") in identifiers
    for stem in ("train", "dev", "test"):
        assert ("no", "bokmaal", "ud", stem) in identifiers
        assert ("no", "bokmaal", "ud", stem, "conllu") in identifiers
    assert ("license",) in identifiers and ("license", "txt") in identifiers
    assert len({n.pedigree_hash(row) for row in n.ALIAS_SEQUENCES}) == len(n.ALIAS_SEQUENCES)


@pytest.mark.parametrize("identifier", n.ALIAS_SEQUENCES)
def test_each_pedigree_identifier_is_an_exact_stop_fixture(identifier):
    assert n.alias_hits(identifier) == [n.pedigree_hash(identifier)]
    assert n.alias_hits(("prefix", *identifier)) == []


def test_private_custody_detects_same_size_substitution(tmp_path, monkeypatch):
    data = tmp_path / "data/msae_independent_norspan_v1"
    monkeypatch.setattr(n, "DATA", data)
    monkeypatch.setattr(n, "PRIVATE", data / "private")
    source = tmp_path / "source.conllu"
    source.write_text(conllu(), "utf-8")
    sentence = n.parse_conllu(source, "train")[0][0]
    roles = {"discovery": [sentence], "calibration": [], "C1": [], "C2": []}
    rendered = n.render_role_payloads(roles)
    n.publish_private_roles(roles)
    n.verify_private_payload_bytes(rendered)
    path = n.PRIVATE / "discovery/payload.jsonl"
    payload = bytearray(path.read_bytes())
    payload[0] ^= 1
    path.write_bytes(payload)
    path.chmod(0o600)
    with pytest.raises(n.GateFailure, match="private_payload_drift"):
        n.verify_private_payload_bytes(rendered)


def test_authority_control_table_is_exact_and_mode_bound():
    assert n.AUTHORITY_CONTROL_MODES == n.load_config()["control_plane"]["authority_control_modes"]
    assert set(n.AUTHORITY_CONTROL_MODES) == {
        "docs/plan-msae-independent-norspan-v1.md",
        "reports/adversarial/msae_independent_norspan_v1_plan_review.md",
        "configs/msae_independent_norspan_v1/protocol.json",
        "scripts/prepare_msae_independent_norspan_v1.py",
        "scripts/acquire_msae_independent_norspan_v1.py",
        "tests/test_prepare_msae_independent_norspan_v1.py",
        "reports/verification/msae_independent_norspan_v1_source_free_checks.log",
        "reports/adversarial/msae_independent_norspan_v1_implementation_review.md",
        "reports/provenance/msae_independent_norspan_v1/current_history_registry.json",
        "reports/provenance/msae_independent_norspan_v1/baseline.json",
    }


def test_scratch_cleanup_is_descriptor_relative(tmp_path):
    import acquire_msae_independent_norspan_v1 as a
    scratch = tmp_path / "scratch"
    (scratch / "nested").mkdir(parents=True)
    (scratch / "nested/file").write_bytes(b"x")
    parent_fd = __import__("os").open(tmp_path, __import__("os").O_RDONLY | __import__("os").O_DIRECTORY)
    scratch_fd = __import__("os").open("scratch", __import__("os").O_RDONLY | __import__("os").O_DIRECTORY,
                                       dir_fd=parent_fd)
    identity = scratch.lstat()
    a.cleanup_scratch(scratch, parent_fd, scratch_fd, identity)
    __import__("os").close(scratch_fd); __import__("os").close(parent_fd)
    assert not scratch.exists()


def _synthetic_sentence_block(group, sent_id, unique):
    return "\n".join([
        f"# newdoc id = {group}", f"# sent_id = {sent_id}",
        f"1\tWord{unique}\tlemma\tNOUN\t_\tNumber=Sing\t2\tnsubj\t_\t_",
        "2\ter\tvære\tAUX\t_\t_\t0\troot\t_\t_",
        "3\ttest\ttest\tNOUN\t_\tNumber=Sing\t2\tobj\t_\t_",
        "4\t.\t.\tPUNCT\t_\t_\t2\tpunct\t_\t_", "",
    ])


def test_compute_science_mixed_registry_end_to_end(tmp_path, monkeypatch):
    cfg = n.load_config()
    groups = {role: [] for role in ("discovery", "calibration", "C1", "C2")}
    i = 0
    while any(len(rows) < 20 for rows in groups.values()):
        group = f"group-{i}"
        role = n.role_for_group(("train", group))[0]
        if len(groups[role]) < 20:
            groups[role].append(group)
        i += 1
    blocks = []
    index = 0
    for role in ("discovery", "calibration", "C1", "C2"):
        for group in groups[role]:
            blocks.append(_synthetic_sentence_block(group, f"train-{index}", index))
            index += 1
    raw = {
        n.SOURCE_FILES["train"]: "\n".join(blocks).encode(),
        n.SOURCE_FILES["dev"]: _synthetic_sentence_block("dev-extra", "dev-0", 1000).encode(),
        n.SOURCE_FILES["test"]: _synthetic_sentence_block("test-extra", "test-0", 1001).encode(),
        n.LICENSE_FILE: b"CC BY-SA 4.0\n",
    }
    protected = tmp_path / "private"
    protected.mkdir()
    st = protected.lstat()
    registry = {
        "blocking_alias_occurrence_count": 0, "alias_occurrences": [],
        "entries": [{"path": "private", "device": st.st_dev, "inode": st.st_ino,
                     "type": stat.S_IFMT(st.st_mode), "mode": stat.S_IMODE(st.st_mode),
                     "nlink": st.st_nlink, "size": st.st_size, "sha256": None,
                     "adapter": "protected_directory_lstat_only", "extracted_unit_count": 0}],
    }
    monkeypatch.setattr(n, "ROOT", tmp_path)
    artifacts, roles = n.compute_science(raw, registry, cfg)
    assert list(artifacts) == list(n.SCIENCE_PREFIX)
    assert artifacts["support.json"]["status"] == "eligible"
    assert all(len(roles[role]) >= 20 for role in roles)
    rendered = n.render_role_payloads(roles)
    assert all(rendered[role].count(b"\n") == len(roles[role]) for role in roles)


@pytest.mark.parametrize("launcher", [b"torchrun", b"accelerate launch", b"deepspeed", b"python train.py", b"python evaluate.py", b"tmux new-session"])
def test_capability_vocabulary_catches_project_launchers(launcher):
    tokens, env = n.process_capability_reasons(launcher + b" " + str(n.ROOT).encode(), str(n.ROOT), b"PATH=/bin\0")
    assert tokens and not env


def test_capability_vocabulary_catches_gpu_environment():
    tokens, env = n.process_capability_reasons(b"python safe.py", str(n.ROOT), b"CUDA_VISIBLE_DEVICES=0\0")
    assert not tokens and env == ["CUDA_VISIBLE_DEVICES"]


def test_acquisition_end_to_end_with_fake_git_no_network(tmp_path, monkeypatch):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    prov = n.PROV
    payloads = {name: (name + "\n").encode() for name in a.FILES}
    blobs = {name: hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
             for name, payload in payloads.items()}
    tree_oid = "a" * 40

    def fake_run(argv, *, env, cwd=None):
        del env, cwd
        if "clone" in argv:
            repo = Path(argv[-1]); repo.mkdir(); (repo / ".git").mkdir()
            return b"", b"", 0
        repo = Path(argv[argv.index("-C") + 1])
        if "checkout" in argv:
            for name, payload in payloads.items():
                (repo / name).write_bytes(payload)
            return b"", b"", 0
        if argv[-2:] == ["rev-parse", "HEAD"]:
            return (n.COMMIT + "\n").encode(), b"", 0
        if "rev-parse" in argv and argv[-1].endswith("^{tree}"):
            return (tree_oid + "\n").encode(), b"", 0
        if "ls-tree" in argv:
            raw = b"".join(f"100644 blob {blobs[name]}\t{name}\0".encode()
                           for name in sorted(a.FILES))
            return raw, b"", 0
        if "cat-file" in argv:
            raw = b"".join(f"{oid} blob {len(payloads[name])}\n".encode()
                           for name, oid in sorted(blobs.items()))
            raw += f"{n.COMMIT} commit 1\n{tree_oid} tree 1\n".encode()
            return raw, b"", 0
        return b"", b"", 0

    monkeypatch.setattr(a, "run", fake_run)
    a.acquire(review_sha)
    acquisition = n.load_json(prov / "source_acquisition.json")
    assert acquisition["sparse_checkout"] is True
    assert acquisition["local_blob_object_ids"] == sorted(blobs.values())
    assert set(path.name for path in n.RAW.iterdir()) == set(a.FILES)
    assert all(stat.S_IMODE((n.RAW / name).stat().st_mode) == 0o444 for name in a.FILES)


def test_single_publisher_preserves_entry_observed_temp(tmp_path):
    target = tmp_path / "value.json"
    temp = tmp_path / ".value.json.building"
    temp.write_bytes(b"retained interruption evidence")
    old = temp.stat()
    with pytest.raises(n.GateFailure, match="create_once_exists"):
        n.publish_bytes(target, b"replacement")
    assert temp.read_bytes() == b"retained interruption evidence"
    assert temp.stat().st_ino == old.st_ino
    assert not target.exists()


def test_flat_publisher_preserves_entry_observed_final(tmp_path):
    target = tmp_path / "retained"
    target.mkdir()
    child = target / "evidence"
    child.write_bytes(b"retained final evidence")
    old = target.stat()
    with pytest.raises(n.GateFailure, match="create_once_exists"):
        n.publish_flat_directory(target, {"new": b"replacement"},
                                 directory_mode=0o700, file_mode=0o600)
    assert target.stat().st_ino == old.st_ino
    assert child.read_bytes() == b"retained final evidence"
    assert set(p.name for p in target.iterdir()) == {"evidence"}


@pytest.mark.parametrize("flat", [False, True])
def test_publication_write_failure_retains_unresolved_evidence(tmp_path, monkeypatch, flat):
    def fail_write(_fd, _payload):
        raise OSError("injected_write_failure")

    monkeypatch.setattr(n.os, "write", fail_write)
    target = tmp_path / "attempt"
    with pytest.raises(OSError, match="injected_write_failure"):
        if flat:
            n.publish_flat_directory(target, {"payload": b"attempted"},
                                     directory_mode=0o700, file_mode=0o600)
        else:
            n.publish_bytes(target, b"attempted")
    if flat:
        assert target.is_dir()
        assert (target / ".payload.building").is_file()
    else:
        assert not target.exists()
        assert (tmp_path / ".attempt.building").is_file()


@pytest.mark.parametrize("payload", [b"hidden\0text", b"\xffhidden"])
def test_unknown_public_binary_fails_closed(tmp_path, payload):
    path = tmp_path / "unknown.dat"
    path.write_bytes(payload)
    with pytest.raises(n.GateFailure, match="unclassifiable_history_binary"):
        n.classify_file(path)


@pytest.mark.parametrize("url", [
    "https\uff1a\uff0f\uff0fcreativecommons\uff0eorg\uff0flicenses\uff0fby-sa\uff0f4\uff0e0",
    "HTTPS://creativecommons.org/licenses/by-sa/4.0",
])
def test_license_url_must_have_literal_ascii_spelling(url):
    report = n.license_evidence(url)
    assert report["accepted_phrase_count"] == 0
    assert report["accepted_url_count"] == 0
    assert report["status"] == "ineligible"


def test_document_marker_cannot_manufacture_sentence_boundary():
    first = conllu(group="one", sent_id="one").rstrip("\n")
    second = conllu(group="two", sent_id="two")
    with pytest.raises(n.GateFailure, match="document_group_mid_sentence"):
        n.parse_conllu_text(first + "\n" + second, "train")


@pytest.mark.parametrize("row_id", ["garbage-range", "bad.node", "0-1", "1-1", "2-1", "1.0", "01", "+1"])
def test_noncanonical_conllu_row_ids_are_rejected(row_id):
    text = conllu().replace("1\tDette", row_id + "\tDette")
    with pytest.raises(n.GateFailure, match="malformed_conllu_row_id"):
        n.parse_conllu_text(text, "train")


def test_canonical_multiword_row_is_counted_and_validated():
    row = "1-2\tDette-er\t_\t_\t_\t_\t_\t_\t_\t_\n"
    text = conllu().replace("1\tDette", row + "1\tDette")
    sentences, counts = n.parse_conllu_text(text, "train")
    assert len(sentences) == 1 and counts["multiword_rows"] == 1


def test_canonical_empty_node_row_is_counted_and_validated():
    row = "1.1\tDette\tdette\tPRON\t_\t_\t_\t_\t2:nsubj\t_\n"
    text = conllu().replace("2\ter", row + "2\ter")
    sentences, counts = n.parse_conllu_text(text, "train")
    assert len(sentences) == 1 and counts["empty_node_rows"] == 1


def test_text_history_nul_is_not_silently_tokenized(tmp_path):
    path = tmp_path / "public.md"
    path.write_bytes(b"readable\0hidden")
    with pytest.raises(n.GateFailure, match="history_text_nul"):
        list(n.history_units(path, "text", n.load_config()))


@pytest.mark.parametrize("offset", [65533, 65534, 65535, 65536])
def test_utf8_probe_boundary_is_valid_text(tmp_path, offset):
    path = tmp_path / "valid.dat"
    path.write_bytes(b"a" * offset + "é文".encode())
    assert n.classify_file(path) == "text"
    assert list(n.history_units(path, "text", n.load_config()))


def test_late_invalid_utf8_is_rejected_by_full_history_adapter(tmp_path):
    path = tmp_path / "invalid.dat"
    path.write_bytes(b"a" * 65537 + b"\xff")
    assert n.classify_file(path) == "text"
    with pytest.raises(n.GateFailure, match="history_non_utf8"):
        list(n.history_units(path, "text", n.load_config()))


def test_private_publisher_retains_partial_evidence(tmp_path, monkeypatch):
    _set_protocol_root(monkeypatch, tmp_path)
    def fail_write(_fd, _data):
        raise OSError("injected_private_write")
    monkeypatch.setattr(n.os, "write", fail_write)
    with pytest.raises(OSError, match="injected_private_write"):
        sentence = n.parse_conllu_text(conllu(), "train")[0][0]
        n.publish_private_roles({role: [sentence] for role in ["discovery", "calibration", "C1", "C2"]})
    assert n.PRIVATE.is_dir()
    assert (n.PRIVATE / "discovery/.payload.jsonl.building").is_file()


def test_private_verifier_never_materializes_actual_payload(tmp_path, monkeypatch):
    _set_protocol_root(monkeypatch, tmp_path)
    rendered = {role: b"" for role in ["discovery", "calibration", "C1", "C2"]}
    n.publish_private_roles({role: [] for role in rendered})
    monkeypatch.setattr(n, "read_bytes_nofollow", lambda *_a, **_k: pytest.fail("private bytes materialized"))
    assert n.verify_private_payload_bytes(rendered)["C2"]["bytes"] == 0


def test_history_recensus_rejects_untracked_or_ignored_addition(tmp_path, monkeypatch):
    cfg = n.load_config()
    _set_protocol_root(monkeypatch, tmp_path)
    (tmp_path / "prior.txt").write_text("unrelated prior record\n")
    registry = n.build_history_registry(cfg)
    (tmp_path / "ignored.txt").write_text("new public record\n")
    with pytest.raises(n.GateFailure, match="history_unexpected_addition"):
        n.validate_history_registry(registry, cfg)


def test_history_recensus_rejects_empty_directory_addition(tmp_path, monkeypatch):
    cfg = n.load_config()
    _set_protocol_root(monkeypatch, tmp_path)
    registry = n.build_history_registry(cfg)
    (tmp_path / "new-empty").mkdir()
    with pytest.raises(n.GateFailure, match="history_unexpected_addition"):
        n.validate_history_registry(registry, cfg)


def test_history_recensus_accepts_exact_baseline_additions(tmp_path, monkeypatch):
    cfg = n.load_config()
    _set_protocol_root(monkeypatch, tmp_path)
    registry = n.build_history_registry(cfg)
    n.PROV.mkdir(parents=True); n.PROV.chmod(0o755)
    for name in ["current_history_registry.json", "baseline.json"]:
        (n.PROV / name).write_text("{}\n"); (n.PROV / name).chmod(0o644)
    observed = n.validate_history_registry(registry, cfg)
    assert observed["state"] == "baseline"
    assert observed["protected_content_reads"] == 0


def test_history_registry_orders_directory_and_dot_sibling(tmp_path, monkeypatch):
    cfg = n.load_config()
    _set_protocol_root(monkeypatch, tmp_path)
    (tmp_path / "a").mkdir(); (tmp_path / "a/z.txt").write_text("child\n")
    (tmp_path / "a.txt").write_text("sibling\n")
    registry = n.build_history_registry(cfg)
    paths = [row["path"] for row in registry["entries"]]
    assert paths == sorted(paths)


def test_history_recensus_rejects_same_size_edit(tmp_path, monkeypatch):
    cfg = n.load_config()
    _set_protocol_root(monkeypatch, tmp_path)
    path = tmp_path / "record.txt"; path.write_bytes(b"alpha")
    registry = n.build_history_registry(cfg)
    path.write_bytes(b"bravo")
    with pytest.raises(n.GateFailure, match="history_hash_drift"):
        n.validate_history_registry(registry, cfg)


def test_raw_loader_uses_one_pinned_directory_for_cardinality_and_files(tmp_path, monkeypatch):
    _set_protocol_root(monkeypatch, tmp_path)
    n.ensure_directory(n.DATA, 0o700); n.ensure_directory(n.DATA / "raw", 0o700)
    payloads = {name: (name + "\n").encode() for name in [*n.SOURCE_FILES.values(), n.LICENSE_FILE]}
    manifest = n.publish_flat_directory(n.RAW, payloads, directory_mode=0o555, file_mode=0o444)
    for name, payload in payloads.items():
        manifest[name]["git_blob_sha1"] = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
    original = n.os.listdir
    def fd_only(path):
        assert isinstance(path, int), "raw cardinality must not use pathname lookup"
        return original(path)
    monkeypatch.setattr(n.os, "listdir", fd_only)
    assert n.load_validated_raw({"files": manifest}) == payloads


def test_public_directory_creation_cannot_follow_symlink_ancestor(tmp_path, monkeypatch):
    _set_protocol_root(monkeypatch, tmp_path)
    outside = tmp_path / "outside"; outside.mkdir(); outside.chmod(0o700)
    (tmp_path / "reports").symlink_to(outside, target_is_directory=True)
    with pytest.raises((OSError, n.GateFailure)):
        n.create_directory_exclusive(n.PROV, 0o755)
    assert list(outside.iterdir()) == []
    assert stat.S_IMODE(outside.stat().st_mode) == 0o700


def _synthetic_authority_root(tmp_path, monkeypatch):
    """Actual files/census/state validators; only host process/Git observations are synthetic."""
    source_root = n.ROOT
    copies = {}
    for rel in {*n.AUTHORITY_CONTROL_MODES, "TODO.md", "scripts/prepare_msae_independent_source_v10.py"}:
        if not rel.startswith("reports/provenance/"):
            copies[rel] = (source_root / rel).read_bytes()
    _set_protocol_root(monkeypatch, tmp_path)
    monkeypatch.setattr(n, "CONFIG_PATH", tmp_path / "configs/msae_independent_norspan_v1/protocol.json")
    for rel, payload in copies.items():
        p = tmp_path / rel; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload); p.chmod(n.AUTHORITY_CONTROL_MODES.get(rel, 0o644))
    (tmp_path / ".git").mkdir(); (tmp_path / ".git/HEAD").write_text("a" * 40 + "\n")
    review = tmp_path / "reports/adversarial/msae_independent_norspan_v1_implementation_review.md"
    review.write_text("VERDICT: SHIP\nSynthetic fixture only; not real authorization.\n"); review.chmod(0o644)
    monkeypatch.setattr(n, "_process_snapshot", lambda: {"scanned_process_count": 1, "prohibited_match_count": 0, "matches": []})
    monkeypatch.setattr(n, "_git_porcelain_snapshot", lambda: {"outside_protocol_count": 0, "outside_protocol_sha256": n.sha_bytes(b"[]")})
    n.cmd_build_history(None)
    n.cmd_build_authority(None)
    authority_review = tmp_path / "reports/adversarial/msae_independent_norspan_v1_authority_review.md"
    authority_review.write_text("VERDICT: SHIP\nSynthetic authority fixture only.\n"); authority_review.chmod(0o644)
    assert n.classify_protocol_state() == "authority"
    return n.sha_file(authority_review)


def test_authority_checks_actual_control_mode(tmp_path, monkeypatch):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    (tmp_path / "scripts/acquire_msae_independent_norspan_v1.py").chmod(0o644)
    with pytest.raises(n.GateFailure):
        a.validate_authority(review_sha)


def test_authority_rejects_source_schema_drift(tmp_path, monkeypatch):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    path = n.PROV / "authority.json"
    obj = n.load_json(path); obj["source_repo"] = "unreviewed replacement"
    path.write_bytes(n.canonical_file_bytes(obj))
    with pytest.raises(n.GateFailure, match="authority"):
        a.validate_authority(review_sha)


def test_authority_reenumerates_ignored_additions_before_network(tmp_path, monkeypatch):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    (tmp_path / "ignored-new.txt").write_text("a new unrelated public history input\n")
    with pytest.raises(n.GateFailure, match="history_unexpected_addition"):
        a.validate_authority(review_sha)


def _eligible_synthetic_source():
    groups = {role: [] for role in ("discovery", "calibration", "C1", "C2")}
    i = 0
    while any(len(rows) < 20 for rows in groups.values()):
        group = f"synthetic-{i}"
        role = n.role_for_group(("train", group))[0]
        if len(groups[role]) < 20:
            groups[role].append(group)
        i += 1
    blocks = [_synthetic_sentence_block(group, f"train-{i}", i)
              for i, group in enumerate(group for rows in groups.values() for group in rows)]
    def opaque(block):
        # The actual control code participates in history: generate synthetic
        # surface forms not present as short historical units. No gate is mocked.
        return block.replace("Word", "Z" + hashlib.sha256(b"synthetic surfaces").hexdigest()).replace(
            "\ter\t", "\t" + "q" + "xz" + "\t").replace(
            "\ttest\t", "\t" + "n" + "opquv" + "\t")
    return {
        n.SOURCE_FILES["train"]: opaque("\n".join(blocks)).encode(),
        n.SOURCE_FILES["dev"]: opaque(_synthetic_sentence_block("dev-extra", "dev-0", 1000)).encode(),
        n.SOURCE_FILES["test"]: opaque(_synthetic_sentence_block("test-extra", "test-0", 1001)).encode(),
        n.LICENSE_FILE: b"CC BY-SA 4.0\n",
    }


def _install_synthetic_git(monkeypatch, payloads, *, failure=None):
    import acquire_msae_independent_norspan_v1 as a
    blobs = {name: hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
             for name, payload in payloads.items()}
    calls = []
    def fake_run(argv, *, env, cwd=None):
        del env, cwd
        calls.append(argv)
        if "clone" in argv:
            if failure == "clone":
                return b"", b"synthetic failure", 128
            repo = Path(argv[-1]); repo.mkdir(); (repo / ".git").mkdir()
            return b"", b"", 0
        repo = Path(argv[argv.index("-C") + 1])
        if "checkout" in argv:
            for name, payload in payloads.items():
                (repo / name).write_bytes(payload)
            return b"", b"", 0
        if argv[-2:] == ["rev-parse", "HEAD"]:
            return (n.COMMIT + "\n").encode(), b"", 0
        if "rev-parse" in argv:
            return ("b" * 40 + "\n").encode(), b"", 0
        if "ls-tree" in argv:
            return b"".join(f"100644 blob {blobs[name]}\t{name}\0".encode()
                            for name in sorted(a.FILES)), b"", 0
        if "cat-file" in argv:
            return (b"".join(f"{oid} blob {len(payloads[name])}\n".encode()
                            for name, oid in sorted(blobs.items()))
                    + f"{n.COMMIT} commit 1\n{'b' * 40} tree 1\n".encode()), b"", 0
        return b"", b"", 0
    monkeypatch.setattr(a, "run", fake_run)
    return calls


def _synthetic_acquired_root(tmp_path, monkeypatch, *, license_bytes=None):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    payloads = _eligible_synthetic_source()
    if license_bytes is not None:
        payloads[n.LICENSE_FILE] = license_bytes
    calls = _install_synthetic_git(monkeypatch, payloads)
    a.acquire(review_sha)
    assert len(calls) == 8
    n.validate_control_chain()
    return calls


def test_actual_prepare_and_verify_success_without_models(tmp_path, monkeypatch, capsys):
    _synthetic_acquired_root(tmp_path, monkeypatch)
    n.cmd_prepare(None)
    n.cmd_verify(None)
    assert 'verified_ready_not_scored' in capsys.readouterr().out
    assert n.classify_protocol_state() == "scientific_terminal"


def test_terminal_rejection_requires_fresh_history(tmp_path, monkeypatch):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    _install_synthetic_git(monkeypatch, _eligible_synthetic_source(), failure="clone")
    with pytest.raises(n.GateFailure, match="source_acquisition_clone"):
        a.acquire(review_sha)
    (tmp_path / "ignored-new.txt").write_text("unrelated new history\n")
    with pytest.raises(n.GateFailure, match="history_unexpected_addition"):
        n.cmd_verify(None)


def test_terminal_success_rejects_changed_claim_flags(tmp_path, monkeypatch):
    _synthetic_acquired_root(tmp_path, monkeypatch)
    n.cmd_prepare(None)
    ready_path = n.PROV / "source_ready.json"
    ready = n.load_json(ready_path); ready["independent_replication_claimed"] = True
    ready_path.write_bytes(n.canonical_file_bytes(ready))
    for name in ["no_training_gate.json", "seal.json"]:
        path = n.PROV / name; obj = n.load_json(path)
        obj["source_ready_sha256"] = n.sha_file(ready_path)
        if name == "seal.json":
            obj["no_training_gate_sha256"] = n.sha_file(n.PROV / "no_training_gate.json")
        path.write_bytes(n.canonical_file_bytes(obj))
    with pytest.raises(n.GateFailure):
        n.cmd_verify(None)


@pytest.mark.parametrize("mode", [0o555, 0o700])
def test_flat_directory_final_mode_is_independent_of_umask(tmp_path, mode):
    old = n.os.umask(0o077)
    try:
        target = tmp_path / f"flat-{mode}"
        n.publish_flat_directory(target, {"record": b"synthetic"}, directory_mode=mode, file_mode=0o444)
        assert stat.S_IMODE(target.stat().st_mode) == mode
        assert (target / "record").read_bytes() == b"synthetic"
    finally:
        n.os.umask(old)


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_git_supervisor_bounds_output(stream):
    import acquire_msae_independent_norspan_v1 as a
    with pytest.raises(a.SupervisionFailure) as caught:
        a.run([sys.executable, "-c", f"import os; os.write({1 if stream == 'stdout' else 2}, b'x'*4096)"],
              env={"PATH": "/usr/bin:/bin"}, timeout_seconds=2,
              stdout_limit_bytes=1024, stderr_limit_bytes=1024)
    assert caught.value.reason == stream + "_limit"
    assert len(caught.value.stdout) <= 1024 and len(caught.value.stderr) <= 1024


def test_git_supervisor_timeout_reaps_owned_process():
    import acquire_msae_independent_norspan_v1 as a
    import time
    start = time.monotonic()
    with pytest.raises(a.SupervisionFailure, match="timeout") as caught:
        a.run([sys.executable, "-c", "import time; time.sleep(30)"],
              env={"PATH": "/usr/bin:/bin"}, timeout_seconds=0.1)
    assert time.monotonic() - start < 2
    assert caught.value.returncode is not None


def test_git_supervisor_concurrently_drains_both_pipes():
    import acquire_msae_independent_norspan_v1 as a
    out, err, code = a.run([sys.executable, "-c", "import os; [(os.write(1,b'o'*4096),os.write(2,b'e'*4096)) for _ in range(32)]"],
                          env={"PATH": "/usr/bin:/bin"}, timeout_seconds=2)
    assert code == 0 and len(out) == len(err) == 131072


@pytest.mark.parametrize("stopped_before", ["pre_network_ready.json", "network_started.json"])
def test_acquisition_resumes_only_pre_start_validated_state(tmp_path, monkeypatch, stopped_before):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    calls = _install_synthetic_git(monkeypatch, _eligible_synthetic_source())
    original = n.publish_json
    def interrupted(path, obj, mode=0o644):
        if path.name == stopped_before:
            raise OSError("synthetic_pre_start_interrupt")
        return original(path, obj, mode)
    monkeypatch.setattr(n, "publish_json", interrupted)
    with pytest.raises(OSError, match="synthetic_pre_start_interrupt"):
        a.acquire(review_sha)
    assert calls == []
    monkeypatch.setattr(n, "publish_json", original)
    a.acquire(review_sha)
    assert len(calls) == 8
    n.validate_control_chain()


def test_acquisition_restart_after_started_never_calls_git(tmp_path, monkeypatch):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    calls = []
    def interrupted(*_a, **_k):
        calls.append(1)
        raise KeyboardInterrupt("synthetic_termination")
    monkeypatch.setattr(a, "run", interrupted)
    with pytest.raises(KeyboardInterrupt):
        a.acquire(review_sha)
    assert len(calls) == 1
    with pytest.raises(n.GateFailure):
        a.acquire(review_sha)
    assert len(calls) == 1


def test_actual_scientific_license_rejection_replays_first_failure(tmp_path, monkeypatch, capsys):
    _synthetic_acquired_root(tmp_path, monkeypatch, license_bytes=b"All rights reserved\n")
    with pytest.raises(n.ScientificGateFailure, match="license_ineligible"):
        n.cmd_prepare(None)
    assert not n.PRIVATE.exists()
    n.cmd_verify(None)
    assert 'verified_rejection' in capsys.readouterr().out
    obj = n.load_json(n.PROV / "rejection.json")
    assert obj["published_scientific_prefix"] == ["source_manifest.json", "license.json"]
    obj["failure_code"] = "support_ineligible"
    (n.PROV / "rejection.json").write_bytes(n.canonical_file_bytes(obj))
    with pytest.raises(n.GateFailure, match="first_failure"):
        n.cmd_verify(None)


def test_acquisition_rejection_checks_fresh_capabilities_and_observation(tmp_path, monkeypatch):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    _install_synthetic_git(monkeypatch, _eligible_synthetic_source(), failure="clone")
    with pytest.raises(n.GateFailure, match="source_acquisition_clone"):
        a.acquire(review_sha)
    n.cmd_verify(None)
    monkeypatch.setattr(n, "_process_snapshot", lambda: {"scanned_process_count": 1, "prohibited_match_count": 1, "matches": [{}]})
    with pytest.raises(n.GateFailure, match="prohibited_process_active"):
        n.cmd_verify(None)
    monkeypatch.setattr(n, "_process_snapshot", lambda: {"scanned_process_count": 1, "prohibited_match_count": 0, "matches": []})
    path = n.PROV / "rejection.json"; obj = n.load_json(path)
    obj["commands"][-1]["exit_status"] = 0
    path.write_bytes(n.canonical_file_bytes(obj))
    with pytest.raises(n.GateFailure, match="command_disposition"):
        n.cmd_verify(None)


@pytest.mark.parametrize("change", ["extra_key", "bool_counter", "hardlink"])
def test_pre_network_resume_rejects_marker_or_custody_drift(tmp_path, monkeypatch, change):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    calls = _install_synthetic_git(monkeypatch, _eligible_synthetic_source())
    original = n.publish_json
    def interrupted(path, obj, mode=0o644):
        if path.name == "network_started.json":
            raise OSError("synthetic_pre_start_interrupt")
        return original(path, obj, mode)
    monkeypatch.setattr(n, "publish_json", interrupted)
    with pytest.raises(OSError):
        a.acquire(review_sha)
    monkeypatch.setattr(n, "publish_json", original)
    path = n.PROV / "acquisition_entry.json"
    if change == "hardlink":
        n.os.link(path, tmp_path / "extra-hardlink")
    else:
        obj = n.load_json(path)
        if change == "extra_key":
            obj["extra"] = "unreviewed"
        else:
            obj["subprocesses_started"] = False
        path.write_bytes(n.canonical_file_bytes(obj))
    with pytest.raises(n.GateFailure):
        a.acquire(review_sha)
    assert calls == []


@pytest.mark.parametrize("stage", ["mkdir", "open", "write", "file_fsync", "promotion", "directory_fsync", "parent_fsync"])
@pytest.mark.parametrize("publisher", ["single", "flat", "private"])
def test_publisher_fault_retains_obstruction_and_prevents_retry(tmp_path, monkeypatch, stage, publisher):
    import errno
    _set_protocol_root(monkeypatch, tmp_path)
    n.ensure_directory(n.DATA, 0o700)
    target = tmp_path / "publication"
    sentence = n.parse_conllu_text(conllu(), "train")[0][0]
    payload = {role: [sentence] for role in ("discovery", "calibration", "C1", "C2")}
    originals = {key: getattr(n.os, key) for key in ["mkdir", "open", "write", "fsync", "link", "unlink"]}
    originals["_rename_noreplace"] = n._rename_noreplace
    fired = []
    # Inject once at the requested invocation boundary. A mkdir/open failure
    # before an object exists is pre-start and safely retryable; later faults
    # must leave a temp/final namespace obstruction, never erase evidence.
    def belongs_fd(fd):
        try:
            return str(tmp_path) in n.os.readlink(f"/proc/self/fd/{fd}")
        except OSError:
            return False
    def wrapper(name):
        def fault(*args, **kwargs):
            eligible = not fired
            if name == "fsync":
                fd = args[0]; st = n.os.fstat(fd)
                if stage == "file_fsync":
                    eligible &= stat.S_ISREG(st.st_mode) and belongs_fd(fd)
                elif stage == "directory_fsync":
                    eligible &= stat.S_ISDIR(st.st_mode) and belongs_fd(fd) and n.os.readlink(f"/proc/self/fd/{fd}") != str(tmp_path)
                else:
                    eligible &= n.os.readlink(f"/proc/self/fd/{fd}") == str(tmp_path if publisher != "private" else n.DATA)
            elif name == "open":
                eligible &= bool(args[1] & n.os.O_CREAT)
            elif name == "mkdir":
                eligible &= args[0] in {target.name, n.PRIVATE.name}
            if eligible:
                fired.append(stage)
                raise OSError(errno.EIO, "synthetic_publication_fault")
            return originals[name](*args, **kwargs)
        return fault
    operation = "fsync" if stage.endswith("fsync") else ("_rename_noreplace" if stage == "promotion" else stage)
    owner = n if operation == "_rename_noreplace" else n.os
    monkeypatch.setattr(owner, operation, wrapper(operation))
    def publish():
        if publisher == "single":
            n.publish_bytes(target, b"synthetic record\n")
        elif publisher == "flat":
            n.publish_flat_directory(target, {"payload": b"synthetic record\n"}, directory_mode=0o700, file_mode=0o600)
        else:
            n.publish_private_roles(payload)
    if publisher == "single" and stage in {"mkdir", "directory_fsync"}:
        # Single-file publication has no new child-directory mkdir/fsync.
        pytest.skip("single-file publisher has no new child directory boundary")
    with pytest.raises(OSError, match="synthetic_publication_fault"):
        publish()
    assert fired == [stage]
    monkeypatch.setattr(owner, operation, originals[operation])
    obstruction = (n.PRIVATE if publisher == "private" else target)
    temp = tmp_path / ".publication.building"
    if obstruction.exists() or temp.exists():
        with pytest.raises(n.GateFailure):
            publish()


def test_scientific_operational_failure_is_unresolved_not_negative(tmp_path, monkeypatch):
    _synthetic_acquired_root(tmp_path, monkeypatch)
    original = n.publish_json
    def fault(path, obj, mode=0o644):
        if path.name == "source_manifest.json":
            raise OSError("synthetic_control_write_fault")
        return original(path, obj, mode)
    monkeypatch.setattr(n, "publish_json", fault)
    with pytest.raises(OSError, match="synthetic_control_write_fault"):
        n.cmd_prepare(None)
    assert not (n.PROV / "rejection.json").exists()
    assert n.classify_protocol_state() == "raw_started"
    monkeypatch.setattr(n, "load_validated_raw", lambda *_a, **_k: pytest.fail("repeat raw access"))
    with pytest.raises(n.GateFailure, match="raw_started_unresolved"):
        n.cmd_prepare(None)


def test_raw_directory_exchange_is_rejected_before_any_file_read(tmp_path, monkeypatch):
    _set_protocol_root(monkeypatch, tmp_path)
    n.ensure_directory(n.DATA, 0o700); n.ensure_directory(n.DATA / "raw", 0o700)
    payloads = {name: b"synthetic" for name in [*n.SOURCE_FILES.values(), n.LICENSE_FILE]}
    manifest = n.publish_flat_directory(n.RAW, payloads, directory_mode=0o555, file_mode=0o444)
    original = n.os.open
    def exchanged(path, flags, *args, **kwargs):
        if path == n.RAW.name:
            n.RAW.rename(n.RAW.with_name("retained-owned-raw"))
            n.RAW.mkdir(); n.RAW.chmod(0o555)
        return original(path, flags, *args, **kwargs)
    monkeypatch.setattr(n.os, "open", exchanged)
    monkeypatch.setattr(n, "read_bytes_nofollow", lambda *_a, **_k: pytest.fail("exchanged raw bytes opened"))
    with pytest.raises(n.GateFailure, match="raw_directory_identity"):
        n.load_validated_raw({"files": manifest})


def test_git_supervisor_terminates_pipe_holding_descendant(tmp_path):
    import acquire_msae_independent_norspan_v1 as a
    import os
    import time
    child_pid = tmp_path / "child-pid"
    script = ("import pathlib,subprocess,sys; "
              "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
              f"pathlib.Path({str(child_pid)!r}).write_text(str(p.pid))")
    with pytest.raises(a.SupervisionFailure, match="timeout"):
        a.run([sys.executable, "-c", script], env={"PATH": "/usr/bin:/bin"}, timeout_seconds=0.5)
    pid = int(child_pid.read_text())
    # An orphan zombie may await the host subreaper: it is dead, not executing.
    for _ in range(50):
        try:
            state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        except FileNotFoundError:
            break
        if state == "Z":
            break
        time.sleep(0.01)
    else:
        os.kill(pid, 9)
        pytest.fail("owned descendant survived supervisor")


@pytest.mark.parametrize("stopped_before", ["pre_raw_ready.json", "raw_access_started.json"])
def test_scientific_resume_only_before_raw_start(tmp_path, monkeypatch, stopped_before):
    _synthetic_acquired_root(tmp_path, monkeypatch)
    original = n.publish_json
    def interrupted(path, obj, mode=0o644):
        if path.name == stopped_before:
            raise OSError("synthetic_pre_raw_interrupt")
        return original(path, obj, mode)
    monkeypatch.setattr(n, "publish_json", interrupted)
    with pytest.raises(OSError, match="synthetic_pre_raw_interrupt"):
        n.cmd_prepare(None)
    monkeypatch.setattr(n, "publish_json", original)
    n.cmd_prepare(None)
    n.cmd_verify(None)


def test_raw_start_marker_interrupt_preserves_no_repeat_access(tmp_path, monkeypatch):
    _synthetic_acquired_root(tmp_path, monkeypatch)
    original = n.publish_json
    def interrupted(path, obj, mode=0o644):
        original(path, obj, mode)
        if path.name == "raw_access_started.json":
            raise OSError("synthetic_post_start_interrupt")
    monkeypatch.setattr(n, "publish_json", interrupted)
    monkeypatch.setattr(n, "load_validated_raw", lambda *_a, **_k: pytest.fail("raw opened after durable interruption"))
    with pytest.raises(OSError, match="synthetic_post_start_interrupt"):
        n.cmd_prepare(None)
    assert n.classify_protocol_state() == "raw_started"
    with pytest.raises(n.GateFailure, match="raw_started_unresolved"):
        n.cmd_prepare(None)


def test_acquisition_rejects_worktree_not_matching_git_blob_before_raw_publication(tmp_path, monkeypatch):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    payloads = _eligible_synthetic_source()
    _install_synthetic_git(monkeypatch, payloads)
    original = a.read_sparse_files
    def changed(repo):
        result = original(repo)
        result[a.FILES[0]] += b"\n# substituted\n"
        return result
    monkeypatch.setattr(a, "read_sparse_files", changed)
    with pytest.raises(n.GateFailure, match="source_blob_custody"):
        a.acquire(review_sha)
    assert not n.DATA.exists()
    assert n.classify_protocol_state() == "network_started"


@pytest.mark.parametrize("mutation", ["missing_commit", "negative_size", "duplicate", "unknown_kind"])
def test_acquisition_strict_object_metadata(tmp_path, monkeypatch, mutation):
    import acquire_msae_independent_norspan_v1 as a
    review_sha = _synthetic_authority_root(tmp_path, monkeypatch)
    _install_synthetic_git(monkeypatch, _eligible_synthetic_source())
    original = a.run
    def changed(argv, **kwargs):
        out, err, code = original(argv, **kwargs)
        if "cat-file" in argv:
            if mutation == "missing_commit":
                out = b"\n".join(row for row in out.splitlines() if b" commit " not in row) + b"\n"
            elif mutation == "negative_size":
                out += f"{'c' * 40} tree -1\n".encode()
            elif mutation == "duplicate":
                out += out.splitlines()[0] + b"\n"
            else:
                out += f"{'c' * 40} mystery 1\n".encode()
        return out, err, code
    monkeypatch.setattr(a, "run", changed)
    with pytest.raises(n.GateFailure, match="object_inventory"):
        a.acquire(review_sha)
    assert not n.DATA.exists()
    assert n.classify_protocol_state() == "network_started"


def test_canonical_control_parses_one_observed_read(tmp_path, monkeypatch):
    path = tmp_path / "control.json"; path.write_bytes(n.canonical_file_bytes({"key": 1})); path.chmod(0o644)
    original = n.read_bytes_nofollow
    calls = []
    def once(*args, **kwargs):
        calls.append(args[0]); assert len(calls) == 1
        return original(*args, **kwargs)
    monkeypatch.setattr(n, "read_bytes_nofollow", once)
    assert n.canonical_control(path, ["key"]) == {"key": 1}


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_control_json_is_rejected(tmp_path, constant):
    path = tmp_path / "invalid.json"; path.write_text('{"value":' + constant + '}\n')
    with pytest.raises(n.GateFailure, match="json_nonfinite"):
        n.load_json(path)


# Independently reproduced runtime-review counterexamples, synthetic roots only.
@pytest.mark.parametrize("key,value", [
    ("source_content_printed", True), ("model_operations", False),
    ("sparse_checkout", 1), ("scratch", {"cleanup_verified": "yes"}),
    ("local_object_type_counts", {"mystery": -999}),
])
def test_acquisition_literal_semantics(tmp_path, monkeypatch, key, value):
    _synthetic_acquired_root(tmp_path, monkeypatch)
    path = n.PROV / "source_acquisition.json"
    record = n.load_json(path)
    record[key] = value
    path.write_bytes(n.canonical_file_bytes(record))
    with pytest.raises(n.GateFailure):
        n.validate_control_chain()


@pytest.mark.parametrize("publisher", ["single", "flat", "private"])
def test_publisher_rejects_substituted_temp_inode(tmp_path, monkeypatch, publisher):
    _set_protocol_root(monkeypatch, tmp_path)
    n.ensure_directory(n.DATA, 0o700)
    original = n._rename_noreplace
    changed = []

    def promote(dfd, src, dst):
        if not changed:
            changed.append(True)
            before = n.os.stat(src, dir_fd=dfd, follow_symlinks=False)
            n.os.rename(src, tmp_path / "retained-original", src_dir_fd=dfd)
            fd = n.os.open(src, n.os.O_WRONLY | n.os.O_CREAT | n.os.O_EXCL,
                           stat.S_IMODE(before.st_mode), dir_fd=dfd)
            try:
                n.os.fchmod(fd, stat.S_IMODE(before.st_mode))
                n.os.write(fd, b"x" * before.st_size)
            finally:
                n.os.close(fd)
        return original(dfd, src, dst)

    monkeypatch.setattr(n, "_rename_noreplace", promote)
    with pytest.raises(n.GateFailure, match="publication_original_inode"):
        if publisher == "single":
            n.publish_bytes(tmp_path / "record", b"alpha")
        elif publisher == "flat":
            n.publish_flat_directory(tmp_path / "flat", {"record": b"alpha"},
                                     directory_mode=0o700, file_mode=0o600)
        else:
            sentence = n.parse_conllu_text(conllu(), "train")[0][0]
            n.publish_private_roles({role: [sentence] for role in ["discovery", "calibration", "C1", "C2"]})
    assert changed == [True]
    assert (tmp_path / "retained-original").is_file()


def test_single_parent_exchange(tmp_path, monkeypatch):
    _set_protocol_root(monkeypatch, tmp_path)
    parent = tmp_path / "named-parent"
    parent.mkdir()
    original = n.os.write
    changed = []

    def write(fd, payload):
        if not changed:
            changed.append(True)
            parent.rename(tmp_path / "retained-parent")
            parent.mkdir()
        return original(fd, payload)

    monkeypatch.setattr(n.os, "write", write)
    with pytest.raises(n.GateFailure, match="parent_chain_drift"):
        n.publish_bytes(parent / "record", b"alpha")
    assert (tmp_path / "retained-parent").exists()


def test_raw_parent_exchange(tmp_path, monkeypatch):
    _set_protocol_root(monkeypatch, tmp_path)
    n.ensure_directory(n.DATA, 0o700)
    n.ensure_directory(n.DATA / "raw", 0o700)
    payloads = {name: b"alpha" for name in [*n.SOURCE_FILES.values(), n.LICENSE_FILE]}
    manifest = n.publish_flat_directory(n.RAW, payloads, directory_mode=0o555, file_mode=0o444)
    for row in manifest.values():
        row["git_blob_sha1"] = hashlib.sha1(b"blob 5\0alpha").hexdigest()
    original = n.read_bytes_nofollow
    changed = []

    def read(*args, **kwargs):
        if not changed:
            changed.append(True)
            n.RAW.parent.rename(n.DATA / "retained-raw-parent")
            n.RAW.parent.mkdir()
        return original(*args, **kwargs)

    monkeypatch.setattr(n, "read_bytes_nofollow", read)
    with pytest.raises(n.GateFailure, match="parent_chain_drift"):
        n.load_validated_raw({"files": manifest})


def test_selector_failure_happens_before_subprocess_creation(monkeypatch):
    import acquire_msae_independent_norspan_v1 as a

    def unavailable():
        raise OSError("synthetic_selector_initialization_failure")

    def no_spawn(*args, **kwargs):
        pytest.fail("child created before supervisor initialized")

    monkeypatch.setattr(a.selectors, "DefaultSelector", unavailable)
    monkeypatch.setattr(a.subprocess, "Popen", no_spawn)
    with pytest.raises(OSError, match="synthetic_selector_initialization_failure"):
        a.run([sys.executable, "-c", "pass"], env={"PATH": "/usr/bin:/bin"})


@pytest.mark.parametrize("mutation", [
    "file_bool_bytes", "file_float_mode", "scratch_bool_device", "scratch_bool_inode",
    "object_bool_bytes", "object_extra_key", "object_unknown_kind", "object_duplicate",
    "object_missing_commit", "object_changed_size", "object_reordered", "count_bool",
])
def test_successful_acquisition_nested_metadata_is_replayed(tmp_path, monkeypatch, mutation):
    _synthetic_acquired_root(tmp_path, monkeypatch)
    path = n.PROV / "source_acquisition.json"
    record = n.load_json(path)
    first = next(iter(record["files"].values()))
    objects = record["local_object_records"]
    if mutation == "file_bool_bytes":
        first["bytes"] = True
    elif mutation == "file_float_mode":
        first["mode"] = float(first["mode"])
    elif mutation == "scratch_bool_device":
        record["scratch"]["device"] = False
    elif mutation == "scratch_bool_inode":
        record["scratch"]["inode"] = True
    elif mutation == "object_bool_bytes":
        objects[0]["bytes"] = False
    elif mutation == "object_extra_key":
        objects[0]["unexpected"] = 0
    elif mutation == "object_unknown_kind":
        objects[0]["kind"] = "mystery"
    elif mutation == "object_duplicate":
        objects.append(dict(objects[0]))
    elif mutation == "object_missing_commit":
        objects[:] = [row for row in objects if row["oid"] != n.COMMIT]
    elif mutation == "object_changed_size":
        next(row for row in objects if row["kind"] == "blob")["bytes"] += 1
    elif mutation == "object_reordered":
        objects.reverse()
    else:
        record["local_object_type_counts"]["commit"] = True
    path.write_bytes(n.canonical_file_bytes(record))
    with pytest.raises(n.GateFailure):
        n.validate_control_chain()


@pytest.mark.parametrize("publisher", ["single", "flat", "private"])
def test_all_publishers_reject_exchanged_nonleaf_ancestor(tmp_path, monkeypatch, publisher):
    _set_protocol_root(monkeypatch, tmp_path)
    n.ensure_directory(n.DATA, 0o700)
    ancestor = tmp_path / "ancestor"
    parent = ancestor / "nested"
    parent.mkdir(parents=True)
    if publisher == "private":
        monkeypatch.setattr(n, "PRIVATE", parent / "private")
    original = n.os.write
    changed = []

    def exchange(fd, payload):
        if not changed:
            changed.append(True)
            ancestor.rename(tmp_path / "retained-ancestor")
            parent.mkdir(parents=True)
        return original(fd, payload)

    monkeypatch.setattr(n.os, "write", exchange)
    with pytest.raises(n.GateFailure, match="parent_chain_drift"):
        if publisher == "single":
            n.publish_bytes(parent / "record", b"alpha")
        elif publisher == "flat":
            n.publish_flat_directory(parent / "flat", {"record": b"alpha"},
                                     directory_mode=0o700, file_mode=0o600)
        else:
            sentence = n.parse_conllu_text(conllu(), "train")[0][0]
            n.publish_private_roles({role: [sentence] for role in ["discovery", "calibration", "C1", "C2"]})
    assert changed == [True]
    assert (tmp_path / "retained-ancestor").is_dir()


@pytest.mark.parametrize("reader", ["read_bytes", "read_prefix", "digest"])
def test_safe_file_readers_reject_detached_ancestor(tmp_path, monkeypatch, reader):
    _set_protocol_root(monkeypatch, tmp_path)
    ancestor = tmp_path / "ancestor"
    parent = ancestor / "nested"
    parent.mkdir(parents=True)
    path = parent / "record"
    path.write_bytes(b"alpha")
    original = n.os.read
    changed = []

    def exchange(fd, limit):
        if not changed:
            changed.append(True)
            ancestor.rename(tmp_path / "retained-ancestor")
            parent.mkdir(parents=True)
        return original(fd, limit)

    monkeypatch.setattr(n.os, "read", exchange)
    with pytest.raises(n.GateFailure, match="parent_chain_drift"):
        if reader == "read_bytes":
            n.read_bytes_nofollow(path)
        elif reader == "read_prefix":
            n.read_prefix_nofollow(path, 3)
        else:
            n.stream_file_digest(path)


def test_retained_parent_descriptors_close_on_success_and_failure(tmp_path, monkeypatch):
    import os
    _set_protocol_root(monkeypatch, tmp_path)
    parent = tmp_path / "a" / "b"
    parent.mkdir(parents=True)
    before = set(os.listdir("/proc/self/fd"))
    n.publish_bytes(parent / "record", b"alpha")
    assert n.read_bytes_nofollow(parent / "record") == b"alpha"
    assert n.stream_file_digest(parent / "record")["bytes"] == 5
    assert n._dir_names(parent) == {"record"}
    n._descriptor_tree(parent)
    list(n._history_objects())
    with pytest.raises(n.GateFailure, match="create_once_exists"):
        n.publish_bytes(parent / "record", b"bravo")
    with pytest.raises(FileNotFoundError):
        n.read_bytes_nofollow(parent / "missing")
    with pytest.raises(FileNotFoundError):
        n._open_parent_fd(parent / "absent" / "missing")
    assert set(os.listdir("/proc/self/fd")) == before


def test_supervisor_registration_failure_kills_and_reaps_owned_leader(monkeypatch):
    import acquire_msae_independent_norspan_v1 as a
    selector = a.selectors.DefaultSelector()
    owned = []
    original = a.subprocess.Popen

    def spawn(*args, **kwargs):
        proc = original(*args, **kwargs)
        owned.append(proc)
        return proc

    def unavailable(*args, **kwargs):
        raise OSError("synthetic_registration_failure")

    monkeypatch.setattr(a.selectors, "DefaultSelector", lambda: selector)
    monkeypatch.setattr(selector, "register", unavailable)
    monkeypatch.setattr(a.subprocess, "Popen", spawn)
    with pytest.raises(OSError, match="synthetic_registration_failure"):
        a.run([sys.executable, "-c", "import time; time.sleep(30)"], env={"PATH": "/usr/bin:/bin"})
    assert len(owned) == 1 and owned[0].returncode is not None
    assert owned[0].stdout.closed and owned[0].stderr.closed
    assert selector.get_map() is None


def test_supervisor_popen_failure_closes_initialized_selector(monkeypatch):
    import acquire_msae_independent_norspan_v1 as a
    selector = a.selectors.DefaultSelector()

    def unavailable(*args, **kwargs):
        raise OSError("synthetic_popen_failure")

    monkeypatch.setattr(a.selectors, "DefaultSelector", lambda: selector)
    monkeypatch.setattr(a.subprocess, "Popen", unavailable)
    with pytest.raises(OSError, match="synthetic_popen_failure"):
        a.run([sys.executable, "-c", "pass"], env={"PATH": "/usr/bin:/bin"})
    assert selector.get_map() is None


@pytest.mark.parametrize("surface", ["inventory", "history"])
def test_directory_walk_rejects_detached_named_ancestor(tmp_path, monkeypatch, surface):
    _set_protocol_root(monkeypatch, tmp_path)
    ancestor = tmp_path / "ancestor"
    parent = ancestor / "nested"
    parent.mkdir(parents=True)
    (parent / "record").write_bytes(b"alpha")
    original = n.os.listdir
    expected = n.os.stat(parent)
    changed = []

    def exchange(fd):
        if (isinstance(fd, int) and n.os.fstat(fd).st_ino == expected.st_ino
                and not changed):
            changed.append(True)
            ancestor.rename(tmp_path / "retained-ancestor")
            parent.mkdir(parents=True)
        return original(fd)

    monkeypatch.setattr(n.os, "listdir", exchange)
    with pytest.raises(n.GateFailure):
        if surface == "inventory":
            n._descriptor_tree(parent)
        else:
            list(n._history_objects())
    assert changed == [True]


def test_directory_root_open_failure_closes_parent_chain(tmp_path, monkeypatch):
    import os
    _set_protocol_root(monkeypatch, tmp_path)
    target = tmp_path / "inventory-root"
    target.mkdir()
    original = n.os.open
    before = set(os.listdir("/proc/self/fd"))

    def unavailable(path, flags, *args, **kwargs):
        if path == target.name:
            raise OSError("synthetic_root_open_failure")
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(n.os, "open", unavailable)
    with pytest.raises(OSError, match="synthetic_root_open_failure"):
        n._descriptor_tree(target)
    assert set(os.listdir("/proc/self/fd")) == before


def _invoke_synthetic_publisher(tmp_path, publisher):
    if publisher == "single":
        n.publish_bytes(tmp_path / "publication", b"alpha")
    elif publisher == "flat":
        n.publish_flat_directory(tmp_path / "publication", {"payload": b"alpha"},
                                 directory_mode=0o700, file_mode=0o600)
    else:
        sentence = n.parse_conllu_text(conllu(), "train")[0][0]
        n.publish_private_roles({role: [sentence] for role in ["discovery", "calibration", "C1", "C2"]})


@pytest.mark.parametrize("publisher", ["single", "flat", "private"])
@pytest.mark.parametrize("attack", ["same_inode", "foreign_temp"])
def test_atomic_publishers_check_bytes_and_never_erase_substituted_temp(tmp_path, monkeypatch, publisher, attack):
    import os
    _set_protocol_root(monkeypatch, tmp_path)
    n.ensure_directory(n.DATA, 0o700)
    original = n._rename_noreplace
    changed = []
    foreign = []
    before_fds = set(os.listdir("/proc/self/fd"))

    def promote(fd, source, destination):
        if changed:
            return original(fd, source, destination)
        changed.append(True)
        if attack == "same_inode":
            st = os.stat(source, dir_fd=fd, follow_symlinks=False)
            writer = os.open(source, os.O_WRONLY, dir_fd=fd)
            try:
                os.write(writer, b"x" * st.st_size)
                os.fsync(writer)
            finally:
                os.close(writer)
            return original(fd, source, destination)
        original(fd, source, destination)
        writer = os.open(source, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600, dir_fd=fd)
        try:
            os.write(writer, b"foreign-evidence")
        finally:
            os.close(writer)
        foreign.append(Path(os.readlink(f"/proc/self/fd/{fd}")) / source)

    monkeypatch.setattr(n, "_rename_noreplace", promote)
    with pytest.raises(n.GateFailure):
        _invoke_synthetic_publisher(tmp_path, publisher)
    assert changed == [True]
    if attack == "foreign_temp":
        assert foreign[0].read_bytes() == b"foreign-evidence"
    assert set(os.listdir("/proc/self/fd")) == before_fds


@pytest.mark.parametrize("publisher", ["single", "flat", "private"])
def test_atomic_publishers_do_not_replace_a_racing_final(tmp_path, monkeypatch, publisher):
    _set_protocol_root(monkeypatch, tmp_path)
    n.ensure_directory(n.DATA, 0o700)
    original = n._rename_noreplace
    raced = []

    def promote(fd, source, destination):
        writer = n.os.open(destination, n.os.O_CREAT | n.os.O_EXCL | n.os.O_WRONLY, 0o600, dir_fd=fd)
        try:
            n.os.write(writer, b"foreign-final")
        finally:
            n.os.close(writer)
        raced.append(Path(n.os.readlink(f"/proc/self/fd/{fd}")) / destination)
        return original(fd, source, destination)

    monkeypatch.setattr(n, "_rename_noreplace", promote)
    with pytest.raises(FileExistsError):
        _invoke_synthetic_publisher(tmp_path, publisher)
    assert raced[0].read_bytes() == b"foreign-final"


@pytest.mark.parametrize("publisher", ["single", "flat", "private"])
@pytest.mark.parametrize("unavailable", ["symbol", "filesystem"])
def test_atomic_publishers_have_no_unsafe_platform_fallback(tmp_path, monkeypatch, publisher, unavailable):
    _set_protocol_root(monkeypatch, tmp_path)
    n.ensure_directory(n.DATA, 0o700)
    if unavailable == "symbol":
        monkeypatch.setattr(n.ctypes, "CDLL", lambda *args, **kwargs: object())
    else:
        class UnsupportedFilesystem:
            def __init__(self):
                self.renameat2 = lambda *args: -1
        monkeypatch.setattr(n.ctypes, "CDLL", lambda *args, **kwargs: UnsupportedFilesystem())
        monkeypatch.setattr(n.ctypes, "get_errno", lambda: n.errno.EINVAL)
    with pytest.raises(n.GateFailure, match="atomic_noreplace_unavailable"):
        _invoke_synthetic_publisher(tmp_path, publisher)
    assert list(tmp_path.rglob("*.building"))


def test_late_single_temp_after_directory_fsync(tmp_path, monkeypatch):
    import os
    _set_protocol_root(monkeypatch, tmp_path)
    original = n.os.fsync
    foreign = tmp_path / ".record.building"
    fired = []

    def fsync(fd):
        result = original(fd)
        if (not fired and (tmp_path / "record").exists()
                and os.readlink(f"/proc/self/fd/{fd}") == str(tmp_path)):
            fired.append(True)
            foreign.write_bytes(b"foreign-late-evidence")
        return result

    monkeypatch.setattr(n.os, "fsync", fsync)
    with pytest.raises(n.GateFailure, match="publication_extra_building_object"):
        n.publish_bytes(tmp_path / "record", b"alpha")
    assert fired == [True]
    assert foreign.read_bytes() == b"foreign-late-evidence"


def test_late_private_root_extra_during_last_digest(tmp_path, monkeypatch):
    import os
    _set_protocol_root(monkeypatch, tmp_path)
    original = n.os.read
    foreign = n.PRIVATE / "foreign-late-evidence"
    reads = []

    def read(fd, count):
        result = original(fd, count)
        if os.readlink(f"/proc/self/fd/{fd}") == str(n.PRIVATE / "c2" / "payload.jsonl") and result:
            reads.append(True)
            if len(reads) == 3:  # Complete-publication digest, not pre-root-list self-checks.
                foreign.write_bytes(b"foreign-late-evidence")
        return result

    monkeypatch.setattr(n.os, "read", read)
    sentence = n.parse_conllu_text(conllu(), "train")[0][0]
    with pytest.raises(n.GateFailure, match="private_publication_cardinality"):
        n.publish_private_roles({role: [sentence] for role in ["discovery", "calibration", "C1", "C2"]})
    assert len(reads) == 3
    assert foreign.read_bytes() == b"foreign-late-evidence"


def test_inventory_root_fstat_failure_does_not_leak_retained_chain(tmp_path, monkeypatch):
    import os
    monkeypatch.setattr(n, "ROOT", tmp_path)
    target = tmp_path / "inventory-root"
    target.mkdir()
    opened = []
    original_open, original_stat = os.open, os.fstat

    def opening(path, flags, *args, **kwargs):
        fd = original_open(path, flags, *args, **kwargs)
        opened.append((fd, original_stat(fd), path))
        return fd

    def unavailable(fd):
        if opened and opened[-1][2] == target.name and fd == opened[-1][0]:
            raise OSError("synthetic_root_fstat_failure")
        return original_stat(fd)

    monkeypatch.setattr(n.os, "open", opening)
    monkeypatch.setattr(n.os, "fstat", unavailable)
    with pytest.raises(OSError, match="synthetic_root_fstat_failure"):
        n._descriptor_tree(target)
    leaked = []
    for fd, expected, _path in opened:
        try:
            actual = original_stat(fd)
        except OSError:
            continue
        if (actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino):
            leaked.append(fd)
    for fd in leaked:
        os.close(fd)  # Only extra owned descriptors, if a regression reintroduces leakage.
    assert leaked == []
