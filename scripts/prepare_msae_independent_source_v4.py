#!/usr/bin/env python3
"""Source-readiness builder for MSAE v4; standard-library and model-free."""
from __future__ import annotations

import argparse
import ast
import codecs
import collections
import ctypes
import dataclasses
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "3ba83a5ded2c2b6e69ea2fa862806a892ae62a53"
REPO = "https://github.com/UniversalDependencies/UD_English-Atis.git"
RAW = ROOT / "data/msae_independent_source_v4/raw" / COMMIT
PRIVATE = ROOT / "data/msae_independent_source_v4/private"
PROV = ROOT / "reports/provenance/msae_independent_source_v4"
QUARANTINES = {
    "data/atlas_v1/private/final.jsonl",
    "data/atlas_v1/private/final.records.jsonl",
    "data/atlas_v1/private/final.units.jsonl",
}
SOURCE_FILES = {
    "train": "en_atis-ud-train.conllu",
    "dev": "en_atis-ud-dev.conllu",
    "test": "en_atis-ud-test.conllu",
}
UPOS = frozenset("ADJ ADP ADV AUX CCONJ DET INTJ NOUN NUM PART PRON PROPN PUNCT SCONJ SYM VERB X".split())
DEPREL = frozenset("acl advcl advmod amod appos aux case cc ccomp clf compound conj cop csubj dep det discourse dislocated expl fixed flat goeswith iobj list mark nmod nsubj nummod obj obl orphan parataxis punct reparandum root vocative xcomp".split())
NUMBER = frozenset("Sing Plur Dual Trial Pauc Grpa Grpl Inv Ptan".split())
TASKS = ("absolute_bucket", "relative_quartile", "token_identity", "lemma_identity",
         "capitalization", "word_length", "punctuation", "sentence_boundary",
         "head_signed_distance", "dependency_depth", "upos_coarse", "deprel_coarse", "number")
REQUIRED = {"absolute_bucket", "relative_quartile", "capitalization", "word_length",
            "punctuation", "sentence_boundary", "head_signed_distance", "upos_coarse"}
OPTIONAL = {"dependency_depth", "deprel_coarse", "number", "token_identity", "lemma_identity"}
GENERATED_PREFIXES = (".git/", ".venv-atlas/", ".pytest_cache/", ".generated/")
V4_PREFIX = "data/msae_independent_source_v4/"
V4_AUTHORITY = {
    "docs/plan-msae-independent-source-v4.md",
    "docs/plan-msae-project-completion-2026-09-14.md",
    "reports/adversarial/msae_independent_source_v4_plan_review.md",
    "scripts/prepare_msae_independent_source_v4.py",
    "tests/test_prepare_msae_independent_source_v4.py",
}
BINARY_SUFFIXES = {".pyc", ".so", ".a", ".pt", ".npy", ".npz", ".pkl", ".png", ".pdf",
                   ".parquet", ".feather", ".orc", ".fits", ".gz", ".zip", ".tar", ".lock"}
LEX = re.compile(r"[^\W_]+", re.UNICODE)
ALIASES = ("ud_english-atis", "english-atis", "en_atis", COMMIT, REPO.casefold())

class GateFailure(RuntimeError):
    pass

@dataclasses.dataclass(frozen=True)
class Token:
    id: int
    form: str
    lemma: str
    upos: str
    feats: str
    head: int
    deprel: str

@dataclasses.dataclass(frozen=True)
class Sentence:
    sent_id: str
    tokens: tuple[Token, ...]
    source_index: int


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_file_bytes(value: Any) -> bytes:
    return canonical_bytes(value) + b"\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_file_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(path, 0o644)


def replace_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_bytes(canonical_file_bytes(value))
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def strict_json(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out = {}
        for k, v in items:
            if k in out:
                raise GateFailure("duplicate_json_member")
            out[k] = v
        return out
    with path.open("r", encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=pairs)


def parse_feats(value: str) -> dict[str, str]:
    if value == "_":
        return {}
    result: dict[str, str] = {}
    for item in value.split("|"):
        if item.count("=") != 1:
            raise GateFailure("malformed_feats")
        key, val = item.split("=", 1)
        if not key or not val or key in result or any(c in val for c in ",|="):
            raise GateFailure("malformed_feats")
        result[key] = val
    if "Number" in result and result["Number"] not in NUMBER:
        raise GateFailure("unknown_number")
    return result


def _finish_sentence(rows: list[Token], sent_id: str | None, index: int) -> Sentence:
    if not rows or not sent_id or any(x in sent_id for x in ("\0", "\n", "\r")):
        raise GateFailure("invalid_sentence_identity")
    if [x.id for x in rows] != list(range(1, len(rows) + 1)):
        raise GateFailure("noncontiguous_token_ids")
    heads = {x.id: x.head for x in rows}
    if sum(x.head == 0 for x in rows) != 1:
        raise GateFailure("root_count")
    for token in rows:
        if token.head not in heads and token.head != 0:
            raise GateFailure("invalid_head")
        seen: set[int] = set()
        cur = token.id
        while cur:
            if cur in seen:
                raise GateFailure("dependency_cycle")
            seen.add(cur)
            cur = heads[cur]
    return Sentence(sent_id, tuple(rows), index)


def parse_conllu(path: Path) -> tuple[list[Sentence], dict[str, int]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as e:
        raise GateFailure("invalid_utf8") from e
    rows: list[Token] = []
    sentences: list[Sentence] = []
    sent_id: str | None = None
    seen_ids: set[str] = set()
    counts = {"integer_tokens": 0, "multiword_rows": 0, "empty_node_rows": 0}
    def flush() -> None:
        nonlocal rows, sent_id
        if not rows and sent_id is None:
            return
        sentence = _finish_sentence(rows, sent_id, len(sentences))
        if sentence.sent_id in seen_ids:
            raise GateFailure("duplicate_sent_id")
        seen_ids.add(sentence.sent_id)
        sentences.append(sentence)
        rows = []
        sent_id = None
    for line in text.splitlines():
        if not line:
            flush(); continue
        if line.startswith("#"):
            if line.startswith("# sent_id = "):
                if sent_id is not None:
                    raise GateFailure("duplicate_sent_id_comment")
                sent_id = line[len("# sent_id = "):]
            continue
        cols = line.split("\t")
        if len(cols) != 10:
            raise GateFailure("malformed_conllu_columns")
        rid = cols[0]
        if "-" in rid:
            counts["multiword_rows"] += 1; continue
        if "." in rid:
            counts["empty_node_rows"] += 1; continue
        try:
            tid, head = int(rid), int(cols[6])
        except ValueError as e:
            raise GateFailure("malformed_integer") from e
        form, lemma, upos, feats, deprel = cols[1], cols[2], cols[3], cols[5], cols[7]
        if not form or lemma == "_" or not lemma or upos not in UPOS or not deprel:
            raise GateFailure("missing_or_unknown_field")
        coarse = deprel.split(":", 1)[0]
        if coarse not in DEPREL:
            raise GateFailure("unknown_deprel")
        parse_feats(feats)
        rows.append(Token(tid, unicodedata.normalize("NFC", form), unicodedata.normalize("NFC", lemma), upos, feats, head, deprel))
        counts["integer_tokens"] += 1
    flush()
    if not sentences:
        raise GateFailure("empty_source")
    return sentences, counts


def _cap(form: str) -> str:
    letters = "".join(c for c in form if c.isalpha())
    if not letters: return "nonalpha"
    if letters.islower(): return "lower"
    if letters.isupper(): return "upper"
    if letters.istitle(): return "title"
    return "mixed"


def _length(form: str) -> str:
    n = len(unicodedata.normalize("NFC", form))
    return "1" if n == 1 else "2" if n == 2 else "3_4" if n <= 4 else "5_7" if n <= 7 else "8p"


def _depth(token_id: int, heads: dict[int, int]) -> str:
    depth = 0; cur = token_id
    while heads[cur]:
        cur = heads[cur]; depth += 1
    return str(depth) if depth <= 3 else "4p"


def sentence_labels(sentence: Sentence) -> list[dict[str, str | None]]:
    n = len(sentence.tokens); heads = {x.id: x.head for x in sentence.tokens}
    out = []
    for tok in sentence.tokens:
        i = tok.id; d = tok.head - i
        head = "ROOT" if tok.head == 0 else ("L" if d < 0 else "R") + ("1_2" if abs(d) <= 2 else "3_4" if abs(d) <= 4 else "5p")
        boundary = "single" if n == 1 else "initial" if i == 1 else "final" if i == n else "interior"
        feats = parse_feats(tok.feats)
        out.append({
            "absolute_bucket": str(min(7, i - 1)),
            "relative_quartile": str(min(3, 4 * (i - 1) // n)),
            "token_identity": tok.form.casefold(), "lemma_identity": tok.lemma.casefold(),
            "capitalization": _cap(tok.form), "word_length": _length(tok.form),
            "punctuation": "PUNCT" if tok.form and all(unicodedata.category(c).startswith("P") for c in tok.form) else "NONPUNCT",
            "sentence_boundary": boundary, "head_signed_distance": head,
            "dependency_depth": _depth(i, heads), "upos_coarse": tok.upos,
            "deprel_coarse": tok.deprel.split(":", 1)[0], "number": feats.get("Number"),
        })
    return out


def normalized_sentence(sentence: Sentence) -> str:
    return " ".join(unicodedata.normalize("NFKC", x.form).casefold() for x in sentence.tokens)


def lexical_tokens(text: str) -> tuple[str, ...]:
    return tuple(x.casefold() for x in LEX.findall(unicodedata.normalize("NFKC", text)))


def fivegrams(tokens: tuple[str, ...]) -> set[tuple[str, ...]]:
    return {tokens[i:i+5] for i in range(max(0, len(tokens) - 4))}


def overlap_reason(candidate: tuple[str, ...], other: tuple[str, ...]) -> str | None:
    if not candidate or not other:
        return None
    if candidate == other:
        return "exact"
    if len(candidate) <= 9 and len(other) > len(candidate):
        if any(other[i:i+len(candidate)] == candidate for i in range(len(other) - len(candidate) + 1)):
            return "contained_short"
    if len(candidate) >= 10 and len(other) >= 10:
        a, b = fivegrams(candidate), fivegrams(other)
        shared = a & b
        if shared and len(shared) / len(a | b) >= .8:
            return "fivegram_jaccard"
        covered: set[int] = set()
        for i in range(len(candidate) - 4):
            if candidate[i:i+5] in b:
                covered.update(range(i, i + 5))
        if len(shared) >= 4 and len(covered) >= 20 and len(covered) / len(candidate) >= .1:
            return "covered_fivegrams"
    return None


def split_key(sent_id: str, normalized: str) -> str:
    if "\0" in sent_id or "\0" in normalized:
        raise GateFailure("nul_split_key")
    return sha_bytes(canonical_bytes(["msae-independent-source-v4/C1C2", sent_id, normalized]))


def assign_split(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keyed = [(split_key(str(x["sent_id"]), str(x["normalized"])), str(x["sent_id"]), x) for x in rows]
    keyed.sort(key=lambda z: (z[0], z[1].encode("utf-8")))
    return [{**x, "split_key_sha256": h, "panel": "C1" if i % 2 == 0 else "C2", "zero_based_rank": i}
            for i, (h, _sid, x) in enumerate(keyed)]


def public_label(task: str, value: str) -> str:
    if task == "token_identity": return sha_bytes(("msae-v4/token\0" + value).encode())
    if task == "lemma_identity": return sha_bytes(("msae-v4/lemma\0" + value).encode())
    return value


def publish_private_jsonl(directory: Path, name: str, records: Iterable[dict[str, Any]]) -> Path:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    target = directory / name
    tmp = directory / ("." + name + ".building")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        for row in records:
            data = canonical_file_bytes(row)
            pos = 0
            while pos < len(data): pos += os.write(fd, data[pos:])
        os.fsync(fd)
    except BaseException:
        os.close(fd); tmp.unlink(missing_ok=True); raise
    else:
        os.close(fd)
    try:
        os.link(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True); raise
    tmp.unlink()
    os.chmod(target, 0o600)
    dfd = os.open(directory, os.O_RDONLY)
    try: os.fsync(dfd)
    finally: os.close(dfd)
    return target


def _file_hash_and_text(path: Path) -> tuple[str, bool]:
    h = hashlib.sha256(); decoder = codecs.getincrementaldecoder("utf-8")("strict"); is_text = True
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
            if is_text:
                if b"\0" in block: is_text = False
                else:
                    try: decoder.decode(block)
                    except UnicodeDecodeError: is_text = False
        if is_text:
            try: decoder.decode(b"", final=True)
            except UnicodeDecodeError: is_text = False
    return h.hexdigest(), is_text


def inventory_one(path: Path, rel: str, quarantines: set[str]) -> dict[str, Any]:
    s = path.lstat()
    base = {"path": rel, "size": s.st_size, "mode": stat.S_IMODE(s.st_mode), "device": s.st_dev,
            "inode": s.st_ino, "nlink": s.st_nlink, "mtime_ns": s.st_mtime_ns}
    if rel in quarantines:
        return {**base, "sha256": None, "disposition": "quarantine", "adapter": "quarantine_lstat_only",
                "content_reads": 0, "extracted_unit_count": 0}
    digest, text = _file_hash_and_text(path)
    if text:
        disp, adapter = "text_scanned", "conllu_sentences" if path.suffix.lower() == ".conllu" else "physical_lines"
    else:
        suffixes = {x.lower() for x in path.suffixes}
        if not suffixes & BINARY_SUFFIXES and path.suffix.lower() not in BINARY_SUFFIXES:
            disp, adapter = "terminal_unsupported", "none"
        else:
            disp, adapter = "binary_unscanned", "opaque_binary"
    return {**base, "sha256": digest, "disposition": disp, "adapter": adapter,
            "content_reads": 1, "extracted_unit_count": 0}


def _walk_paths() -> Iterator[tuple[Path, str]]:
    for base, dirs, files in os.walk(ROOT):
        root = Path(base)
        relbase = root.relative_to(ROOT).as_posix()
        prefix = "" if relbase == "." else relbase + "/"
        dirs[:] = sorted(d for d in dirs if not any((prefix + d + "/").startswith(x) for x in GENERATED_PREFIXES))
        for name in sorted(files):
            p = root / name; rel = p.relative_to(ROOT).as_posix()
            if rel.startswith(".git/"): continue
            yield p, rel


def inventory_repository() -> dict[str, Any]:
    paths = list(_walk_paths())
    by_inode: dict[tuple[int, int], list[tuple[Path, str, os.stat_result]]] = collections.defaultdict(list)
    special = []
    for p, rel in paths:
        s = p.lstat()
        if stat.S_ISLNK(s.st_mode) or not stat.S_ISREG(s.st_mode):
            special.append(rel); continue
        by_inode[(s.st_dev, s.st_ino)].append((p, rel, s))
    if special: raise GateFailure("special_paths")
    entries = []
    for key in sorted(by_inode, key=lambda z: min(x[1] for x in by_inode[z])):
        group = sorted(by_inode[key], key=lambda z: z[1]); aliases = [x[1] for x in group]
        if group[0][2].st_nlink != len(group): raise GateFailure("external_hardlink_alias")
        if QUARANTINES.intersection(aliases) and len(group) != 1: raise GateFailure("quarantine_alias")
        rep = inventory_one(group[0][0], group[0][1], QUARANTINES)
        for _p, rel, s in group:
            item = dict(rep); item.update({"path": rel, "mode": stat.S_IMODE(s.st_mode), "size": s.st_size,
                                           "mtime_ns": s.st_mtime_ns, "nlink": s.st_nlink,
                                           "hardlink_aliases": aliases if len(aliases) > 1 else []})
            if rel in QUARANTINES: item = inventory_one(_p, rel, QUARANTINES)
            elif rel.startswith(V4_PREFIX): item.update(disposition="v4_excluded", adapter="excluded", extracted_unit_count=0)
            elif rel in V4_AUTHORITY or rel.startswith("reports/adversarial/msae_independent_source_v4_"):
                item.update(disposition="v4_authority", adapter="authority", extracted_unit_count=0)
            entries.append(item)
    counts = collections.Counter(x["disposition"] for x in entries)
    if counts["terminal_unsupported"]: raise GateFailure("unsupported_files")
    return {"schema_version": "msae_independent_source_v4_baseline_inventory_v1",
            "baseline_head": "7e1a6fc7a26a870a4edcf29c96b7cdf3cdbd7faa",
            "entry_count": len(entries), "counts": dict(sorted(counts.items())),
            "quarantine_content_reads": 0, "entries": entries,
            "entries_sha256": sha_bytes(canonical_bytes(entries)), "status": "eligible"}


def _history_units(path: Path, adapter: str) -> Iterator[tuple[str, ...]]:
    if adapter == "conllu_sentences":
        words: list[str] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n\r")
                if not line:
                    if words: yield tuple(x for w in words for x in lexical_tokens(w)); words=[]
                elif not line.startswith("#"):
                    cols = line.split("\t")
                    if len(cols) == 10 and cols[0].isdigit(): words.append(cols[1])
        if words: yield tuple(x for w in words for x in lexical_tokens(w))
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            tokens = lexical_tokens(line)
            if tokens: yield tokens


def _all_source() -> tuple[dict[str, list[Sentence]], dict[str, Any]]:
    roles: dict[str, list[Sentence]] = {}
    counts = {}
    for upstream, name in SOURCE_FILES.items():
        sentences, c = parse_conllu(RAW / name)
        role = "discovery" if upstream == "train" else "calibration" if upstream == "dev" else "test"
        roles[role] = sentences; counts[upstream] = {**c, "sentences": len(sentences), "sha256": sha_file(RAW/name)}
    return roles, counts


def _source_rows(roles: dict[str, list[Sentence]]) -> dict[str, list[dict[str, Any]]]:
    test = assign_split([{"sent_id": s.sent_id, "normalized": normalized_sentence(s), "sentence": s} for s in roles["test"]])
    out = {"discovery": [{"sent_id":s.sent_id,"normalized":normalized_sentence(s),"sentence":s} for s in roles["discovery"]],
           "calibration": [{"sent_id":s.sent_id,"normalized":normalized_sentence(s),"sentence":s} for s in roles["calibration"]],
           "C1": [], "C2": []}
    for row in test: out[row["panel"]].append(row)
    return out


def _role_overlap(rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, str]]:
    roles = ("discovery", "calibration", "C1", "C2"); hits=[]
    for ai in range(len(roles)):
        for bi in range(ai+1,len(roles)):
            a,b=roles[ai],roles[bi]
            for ar in rows[a]:
                at=lexical_tokens(ar["normalized"])
                for br in rows[b]:
                    bt=lexical_tokens(br["normalized"])
                    for cr,ct,orr,ot in ((ar,at,br,bt),(br,bt,ar,at)):
                        reason=overlap_reason(ct,ot)
                        if reason: hits.append({"candidate_role":a if cr is ar else b,"candidate_id":cr["sent_id"],"other_role":b if orr is br else a,"other_id":orr["sent_id"],"reason":reason})
                        if len(hits)>=100:return hits
    return hits


def _history_overlap(rows: dict[str, list[dict[str, Any]]], inventory: dict[str, Any]) -> tuple[list[dict[str,str]], int]:
    candidates=[]
    for role, vals in rows.items():
        for row in vals: candidates.append((role,row["sent_id"],lexical_tokens(row["normalized"])))
    exact=collections.defaultdict(list); shorts=collections.defaultdict(lambda:collections.defaultdict(list)); inv=collections.defaultdict(set); cgrams=[]
    for i,(role,sid,tok) in enumerate(candidates):
        exact[tok].append(i)
        if len(tok)<=9: shorts[len(tok)][tok].append(i)
        gs=fivegrams(tok); cgrams.append(gs)
        for g in gs: inv[g].add(i)
    hits=[]; units=0
    by_path={x["path"]:x for x in inventory["entries"]}
    for rel,item in sorted(by_path.items()):
        if item["disposition"]!="text_scanned":continue
        p=ROOT/rel
        before=p.stat()
        count=0
        for other in _history_units(p,item["adapter"]):
            count+=1;units+=1
            ids=set(exact.get(other,()))
            for n,lookup in shorts.items():
                if len(other)>n:
                    for j in range(len(other)-n+1): ids.update(lookup.get(other[j:j+n],()))
            og=fivegrams(other)
            for g in og:ids.update(inv.get(g,()))
            for i in sorted(ids):
                role,sid,ct=candidates[i];reason=overlap_reason(ct,other)
                if reason:hits.append({"role":role,"sent_id":sid,"history_path":rel,"reason":reason})
                if len(hits)>=100:return hits,units
        item["extracted_unit_count"]=count
        after=p.stat()
        if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):raise GateFailure("history_mutated")
    return hits,units


def _support(rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result={};intersection=set(TASKS)
    for role,vals in rows.items():
        per={}
        for task in TASKS:
            classes: dict[str,set[str]]=collections.defaultdict(set)
            for row in vals:
                for labels in sentence_labels(row["sentence"]):
                    val=labels[task]
                    if val is not None:classes[str(val)].add(row["sent_id"])
            retained={public_label(task,k):len(v) for k,v in classes.items() if len(v)>=20}
            eligible=len(retained)>=2
            per[task]={"eligible":eligible,"retained_class_count":len(retained),"distinct_utterances_by_class":dict(sorted(retained.items()))}
            if not eligible:intersection.discard(task)
        result[role]={"utterance_count":len(vals),"tasks":per}
    passed=REQUIRED<=intersection and len(OPTIONAL&intersection)>=2
    return {"schema_version":"msae_independent_source_v4_support_v1","floor_distinct_utterances":20,
            "roles":result,"all_role_task_intersection":sorted(intersection),"status":"eligible" if passed else "ineligible"}


def _token_objects(sentence: Sentence) -> list[dict[str,Any]]:
    return [{"id":t.id,"form":t.form,"lemma":t.lemma,"upos":t.upos,"head":t.head,"deprel":t.deprel,"feats":t.feats} for t in sentence.tokens]


def _source_record_hash(sentence: Sentence) -> str:
    return sha_bytes(canonical_bytes(_token_objects(sentence)))


def _license() -> dict[str,Any]:
    lp=RAW/"LICENSE.txt";rp=RAW/"README.md"
    text=lp.read_text(encoding="utf-8").casefold();readme=rp.read_text(encoding="utf-8").casefold()
    ok=("creative commons attribution-sharealike 4.0" in text or "creativecommons.org/licenses/by-sa/4.0" in text or "cc by-sa 4.0" in text)
    ok=ok and ("cc by-sa 4.0" in readme or "creativecommons.org/licenses/by-sa/4.0" in readme)
    return {"schema_version":"msae_independent_source_v4_license_v1","license_id":"CC-BY-SA-4.0",
            "license_path":"LICENSE.txt","license_sha256":sha_file(lp),"readme_sha256":sha_file(rp),
            "license_url":"https://creativecommons.org/licenses/by-sa/4.0/",
            "obligations":["attribution","share_alike"],"raw_committed":False,"payload_committed":False,
            "status":"eligible" if ok else "ineligible"}


def _source_family(inventory: dict[str,Any], raw_hashes:set[str]) -> dict[str,Any]:
    matches=[];whole=[]
    for item in inventory["entries"]:
        rel=item["path"]
        if item.get("sha256") in raw_hashes:whole.append(rel)
        if item["disposition"]!="text_scanned":continue
        p=ROOT/rel
        with p.open("r",encoding="utf-8") as f:
            for number,line in enumerate(f,1):
                low=line.casefold();found=[a for a in ALIASES if a in low]
                if re.search(r"\batis\b",low):found.append("ATIS")
                if found:matches.append({"path":rel,"line":number,"aliases":sorted(set(found))})
    allowed_paths=V4_AUTHORITY|{"PLAN_ATTEMPT13.md","PLAN_RELATIONAL_EDGE_V1.md","reports/provenance/relational_attention_edges_v1_discovery1_plan_snapshot.md"}
    unexpected=[x for x in matches if x["path"] not in allowed_paths and not x["path"].startswith("reports/adversarial/msae_independent_source_v4_")]
    return {"schema_version":"msae_independent_source_v4_source_family_v1","status":"eligible" if not unexpected and not whole else "ineligible",
            "disposition":"previously_considered_but_project_source_use_unseen","planning_or_authority_matches":matches,
            "unexpected_matches":unexpected,"whole_file_digest_matches":whole}


def validate_static_contract(path: Path) -> list[str]:
    tree=ast.parse(path.read_text(encoding="utf-8"));bad=[]
    forbidden_imports={"torch","transformers","jax","tensorflow","socket","subprocess","requests","urllib"}
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[x.name.split('.')[0] for x in node.names] if isinstance(node,ast.Import) else [(node.module or '').split('.')[0]]
            for name in names:
                if name in forbidden_imports:bad.append("forbidden_import:"+name)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {"eval","exec","__import__"}:bad.append("dynamic_call:"+node.func.id)
    return sorted(bad)


def build_baseline() -> None:
    if sys.version_info[:3] != (3,12,3) or unicodedata.unidata_version != "15.0.0":raise GateFailure("runtime_drift")
    inv=inventory_repository(); replace_json(PROV/"baseline_inventory.json",inv)


def build_ready() -> None:
    if validate_static_contract(Path(__file__)):raise GateFailure("static_contract")
    inv=strict_json(PROV/"baseline_inventory.json")
    roles,source_counts=_all_source(); rows=_source_rows(roles)
    normalized=[]
    for role in rows:
        normalized.extend(x["normalized"] for x in rows[role])
    if len(normalized)!=len(set(normalized)):raise GateFailure("duplicate_normalized_utterance")
    lic=_license(); replace_json(PROV/"license.json",lic)
    if lic["status"]!="eligible":raise GateFailure("license_ineligible")
    raw_hashes={sha_file(RAW/name) for name in [*SOURCE_FILES.values(),"README.md","LICENSE.txt"]}
    fam=_source_family(inv,raw_hashes);replace_json(PROV/"source_family.json",fam)
    if fam["status"]!="eligible":raise GateFailure("source_family_ineligible")
    cross=_role_overlap(rows);replace_json(PROV/"cross_role_overlap.json",{"schema_version":"msae_independent_source_v4_cross_role_overlap_v1","blocking_collision_count":len(cross),"blocking_collisions":cross,"status":"eligible" if not cross else "ineligible"})
    if cross:raise GateFailure("cross_role_overlap")
    hits,unit_count=_history_overlap(rows,inv)
    inv["entries_sha256"]=sha_bytes(canonical_bytes(inv["entries"]));replace_json(PROV/"history_manifest.json",inv)
    overlap={"schema_version":"msae_independent_source_v4_history_overlap_v1","history_unit_count":unit_count,"candidate_utterance_count":sum(map(len,rows.values())),"blocking_collision_count":len(hits),"blocking_collisions":hits,"quarantine_content_reads":0,"status":"eligible" if not hits else "ineligible"}
    replace_json(PROV/"history_overlap.json",overlap)
    if hits:raise GateFailure("history_overlap")
    support=_support(rows);replace_json(PROV/"support.json",support)
    if support["status"]!="eligible":raise GateFailure("support_ineligible")
    role_manifest={"schema_version":"msae_independent_source_v4_role_manifest_v1","source_commit":COMMIT,"roles":{}}
    for role,upstream in (("discovery","train"),("calibration","dev")):
        vals=rows[role];role_manifest["roles"][role]={"upstream_partition":upstream,"record_count":len(vals),"entries":[{"zero_based_rank":i,"sent_id":x["sent_id"],"source_record_sha256":_source_record_hash(x["sentence"])} for i,x in enumerate(vals)]}
    replace_json(PROV/"role_manifest.json",role_manifest)
    test_rows=assign_split([{"sent_id":s.sent_id,"normalized":normalized_sentence(s),"sentence":s} for s in roles["test"]])
    split={"schema_version":"msae_independent_source_v4_split_manifest_v1","source_commit":COMMIT,"split_algorithm":"sha256-canonical-json-array-v1-even-C1-odd-C2","record_count":len(test_rows),"C1_count":sum(x["panel"]=="C1" for x in test_rows),"C2_count":sum(x["panel"]=="C2" for x in test_rows),"entries":[{"sent_id":x["sent_id"],"panel":x["panel"],"zero_based_rank":x["zero_based_rank"],"split_key_sha256":x["split_key_sha256"]} for x in test_rows]}
    replace_json(PROV/"split_manifest.json",split)
    payload_records=({"schema_version":"msae_independent_source_v4_payload_v1","source_repo":REPO,"source_commit":COMMIT,"upstream_partition":"test","panel":x["panel"],"split_key_sha256":x["split_key_sha256"],"sent_id":x["sent_id"],"tokens":_token_objects(x["sentence"])} for x in test_rows)
    payload=publish_private_jsonl(PRIVATE,"blind_payload.jsonl",payload_records)
    ps=payload.lstat()
    acquisition={"schema_version":"msae_independent_source_v4_acquisition_v1","source_repo":REPO,"source_commit":COMMIT,"files":source_counts|{"README.md":{"sha256":sha_file(RAW/'README.md')},"LICENSE.txt":{"sha256":sha_file(RAW/'LICENSE.txt')}},"source_content_printed":False,"status":"eligible"}
    replace_json(PROV/"source_acquisition.json",acquisition)
    artifact_names=["baseline_inventory.json","source_acquisition.json","source_family.json","license.json","history_manifest.json","history_overlap.json","cross_role_overlap.json","support.json","role_manifest.json","split_manifest.json"]
    bindings={n:sha_file(PROV/n) for n in artifact_names}
    plan_sha=sha_file(ROOT/"docs/plan-msae-independent-source-v4.md");review_sha=sha_file(ROOT/"reports/adversarial/msae_independent_source_v4_plan_review.md")
    seal={"schema_version":"msae_independent_source_v4_seal_v1","status":"independent_source_ready_for_future_prescore_protocol","plan_sha256":plan_sha,"plan_review_sha256":review_sha,"program_sha256":sha_file(Path(__file__)),"test_sha256":sha_file(ROOT/'tests/test_prepare_msae_independent_source_v4.py'),"artifact_sha256":bindings,"payload":{"path":"data/msae_independent_source_v4/private/blind_payload.jsonl","sha256":sha_file(payload),"size":ps.st_size,"record_count":len(test_rows),"mode":stat.S_IMODE(ps.st_mode),"nlink":ps.st_nlink},"model_operations":0,"gpu_queries":0,"training_runs":0,"unsupported_tasks":["neutral_prefix_offset","entity_binary","entity_type","source_genre"],"opaque_binary_history_excluded":True}
    replace_json(PROV/"seal.json",seal)
    replace_json(PROV/"no_training_gate.json",{"schema_version":"msae_independent_source_v4_no_training_gate_v1","status":"independent_source_ready_for_future_prescore_protocol","model_scoring_authorized":False,"k2_or_branch_training_authorized":False,"stage_c_authorized":False,"seal_sha256":sha_file(PROV/'seal.json')})


def main() -> None:
    p=argparse.ArgumentParser();p.add_argument("command",choices=("baseline","prepare","verify"));a=p.parse_args()
    if a.command=="baseline":build_baseline()
    elif a.command=="prepare":build_ready()
    else:
        seal=strict_json(PROV/"seal.json");payload=ROOT/seal["payload"]["path"]
        s=payload.lstat()
        if not stat.S_ISREG(s.st_mode) or stat.S_IMODE(s.st_mode)!=0o600 or s.st_nlink!=1 or sha_file(payload)!=seal["payload"]["sha256"]:raise GateFailure("payload_verification")

if __name__ == "__main__":
    main()
