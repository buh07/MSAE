#!/usr/bin/env python3
"""Proxy-to-control benchmark v1.

This is an isolated, create-once benchmark.  It does not import or write any historical attempt,
relational-v4, or proposed-v5 namespace.  Scientific claims require the post-result review that is
deliberately outside this runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
PLAN = ROOT / "PLAN_PROXY_CONTROL_BENCHMARK_V1.md"
PLAN_REVIEW = ROOT / "reports/adversarial/proxy_control_benchmark_v1_plan_review.md"
TEST = ROOT / "tests/test_proxy_control_benchmark_v1.py"
LAUNCHER = ROOT / "scripts/launch_proxy_control_benchmark_v1_tmux.sh"
AMENDMENT = ROOT / "prereg/proxy_control_benchmark_v1_preopening_amendment.md"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def exclusive_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json(value) + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(raw)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError("short write")
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(canonical_json(value) + b"\n")
    os.replace(tmp, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def stable_seed(*parts: object) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16], 16) % (2**31 - 1)


def seed_everything(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


class TopKBranch(nn.Module):
    def __init__(self, width: int, atoms: int, k: int) -> None:
        super().__init__()
        self.width, self.atoms, self.k = width, atoms, k
        self.encoder = nn.Linear(width, atoms)
        self.decoder = nn.Parameter(torch.empty(atoms, width))
        nn.init.kaiming_uniform_(self.encoder.weight, a=math.sqrt(5))
        nn.init.normal_(self.decoder, std=1.0 / math.sqrt(width))

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        pre = torch.relu(self.encoder(x))
        k = min(self.k, pre.shape[-1])
        values, indices = torch.topk(pre, k=k, dim=-1, sorted=False)
        code = torch.zeros_like(pre).scatter(-1, indices, values)
        return code @ self.decoder, code

    @torch.no_grad()
    def normalize_decoder(self) -> None:
        self.decoder.div_(self.decoder.norm(dim=1, keepdim=True).clamp_min(1e-8))


class LearnedDecomposition(nn.Module):
    def __init__(self, width: int, multipliers: Sequence[int], topks: Sequence[int]) -> None:
        super().__init__()
        if len(multipliers) != len(topks):
            raise ValueError("branch specification mismatch")
        self.branches = nn.ModuleList([TopKBranch(width, width * int(m), int(k)) for m, k in zip(multipliers, topks)])

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, list[torch.Tensor], list[torch.Tensor]]:
        pairs = [b(x) for b in self.branches]
        recons = [p[0] for p in pairs]
        return torch.stack(recons).sum(0), recons, [p[1] for p in pairs]

    @torch.no_grad()
    def normalize_decoders(self) -> None:
        for b in self.branches:
            b.normalize_decoder()


def assign_k2_branch(delta_a: np.ndarray, delta_b: np.ndarray) -> int:
    a = float(np.mean(np.linalg.norm(delta_a, axis=-1)))
    b = float(np.mean(np.linalg.norm(delta_b, axis=-1)))
    return 0 if a >= b else 1


def centered_cka(a: np.ndarray, b: np.ndarray) -> float:
    if a.ndim != 2 or b.ndim != 2 or a.shape[0] != b.shape[0]:
        raise ValueError("CKA matrices must share rows")
    x = np.asarray(a, np.float64) - np.mean(a, axis=0, keepdims=True)
    y = np.asarray(b, np.float64) - np.mean(b, axis=0, keepdims=True)
    xy = x.T @ y
    xx = x.T @ x
    yy = y.T @ y
    den = math.sqrt(float(np.sum(xx * xx)) * float(np.sum(yy * yy)))
    return float(np.sum(xy * xy) / den) if den > 1e-15 else float("nan")


def bootstrap_interval(values: Sequence[float], draws: int, seed: int) -> tuple[float, float, float]:
    x = np.asarray(values, np.float64)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return (float("nan"),) * 3
    rng = np.random.default_rng(seed)
    boot = np.asarray([np.mean(x[rng.integers(0, x.size, x.size)]) for _ in range(draws)])
    q = np.quantile(boot, [0.025, 0.5, 0.975], method="linear")
    return tuple(map(float, q))


def classify_equivalence(low: float, high: float, smallest: float) -> str:
    if not np.isfinite([low, high]).all():
        return "INELIGIBLE"
    if low > smallest:
        return "POSITIVE_MATERIAL"
    if high < -smallest:
        return "NEGATIVE_MATERIAL"
    if low > -smallest and high < smallest:
        return "EQUIVALENT_SMALL"
    return "INCONCLUSIVE"


def _source_words(source: str) -> dict[str, list[str]]:
    if source == "SOURCE_A":
        return {
            "names": ["Alice", "Bruno", "Clara", "David", "Elena", "Felix", "Grace", "Henry"],
            "entities": ["cat", "dog", "horse", "cow", "bird", "lion", "wolf", "duck"],
            "answers": [" red", " blue", " green", " black", " white", " gold", " brown", " pink"],
            "fillers": ["After a short pause.", "During the quiet meeting.", "As everyone waited.", "Before the final note."],
            "prefix": ["Archive", "Ledger", "Memo", "Record"],
        }
    if source == "SOURCE_B":
        return {
            "names": ["Iris", "Jonas", "Karla", "Liam", "Marta", "Noah", "Olga", "Pavel"],
            "entities": ["piano", "violin", "drum", "flute", "harp", "trumpet", "cello", "organ"],
            "answers": [" north", " south", " east", " west", " one", " two", " three", " four"],
            "fillers": ["Later the room became calm.", "Meanwhile the group took notes.", "Afterward the clock kept moving.", "Before long the report continued."],
            "prefix": ["Bulletin", "Register", "Summary", "Journal"],
        }
    raise ValueError(source)


def make_controlled_specs(seed: int, source: str, per_concept: int) -> list[dict[str, Any]]:
    words = _source_words(source)
    rng = np.random.default_rng(stable_seed(seed, source, "controlled"))
    candidates: list[dict[str, Any]] = []
    total = max(per_concept * 4, per_concept + 32)
    for i in range(total):
        n = words["names"][i % len(words["names"])]
        n2 = words["names"][(i + 3) % len(words["names"])]
        a = words["answers"][i % len(words["answers"])]
        a2 = words["answers"][(i + 3) % len(words["answers"])]
        ent = words["entities"][i % len(words["entities"])]
        ent2 = words["entities"][(i + 5) % len(words["entities"])]
        fill = words["fillers"][i % len(words["fillers"])]
        tag = words["prefix"][i % len(words["prefix"])]
        nonce = int(rng.integers(1000, 9999))
        candidates.extend([
            {"source": source, "concept": "context", "component_id": f"{source}:context:{i:04d}",
             "base_prompt": f"{tag} {nonce}: {n} selected{a}. Question: What did {n} select? Answer:",
             "cf_prompt": f"{tag} {nonce}: {n} selected{a2}. Question: What did {n} select? Answer:",
             "sham_prompt": f"{tag} {nonce}: {n2} selected{a2}. Question: What did {n} select? Answer:",
             "answer_base": a, "answer_cf": a2},
            {"source": source, "concept": "lexical", "component_id": f"{source}:lexical:{i:04d}",
             "base_prompt": f"Vocabulary {nonce}: the symbol for {ent} is{a}. The symbol for {ent} is",
             "cf_prompt": f"Vocabulary {nonce}: the symbol for {ent2} is{a2}. The symbol for {ent2} is",
             "sham_prompt": f"Vocabulary {nonce}: the symbol for {ent} is{a}. The symbol for {ent} is",
             "answer_base": a, "answer_cf": a2},
            {"source": source, "concept": "relative_position", "component_id": f"{source}:relative:{i:04d}",
             "base_prompt": f"Code {nonce}: {n} uses{a}. Recall: {n} uses",
             "cf_prompt": f"Code {nonce}: {n} uses{a}. {fill} Recall: {n} uses",
             "sham_prompt": f"Code {nonce}: {n} uses{a}. {fill} Recall: {n2} uses",
             "answer_base": a, "answer_cf": a2},
        ])
    out: list[dict[str, Any]] = []
    for concept in ("relative_position", "lexical", "context"):
        rows = [r for r in candidates if r["concept"] == concept]
        out.extend(rows[:per_concept])
    return out


def materialize_panel(tokenizer: Any, cfg: Mapping[str, Any], source: str) -> list[dict[str, Any]]:
    pcfg = cfg["panel"]
    needed = int(pcfg["development_components_per_concept"]) + int(pcfg["test_components_per_concept"])
    specs = make_controlled_specs(int(cfg["seed"]), source, needed * int(pcfg["candidate_multiplier"]))
    out: list[dict[str, Any]] = []
    for concept in cfg["concepts"]:
        kept = 0
        for r in [x for x in specs if x["concept"] == concept]:
            ab = tokenizer(r["answer_base"], add_special_tokens=False)["input_ids"]
            ac = tokenizer(r["answer_cf"], add_special_tokens=False)["input_ids"]
            lengths = [len(tokenizer(r[k], add_special_tokens=False)["input_ids"]) for k in ("base_prompt", "cf_prompt", "sham_prompt")]
            if len(ab) != 1 or len(ac) != 1 or max(lengths) > int(pcfg["maximum_length"]):
                continue
            row = dict(r)
            row.update({"answer_base_id": int(ab[0]), "answer_cf_id": int(ac[0]),
                        "split": "development" if kept < int(pcfg["development_components_per_concept"]) else "test"})
            out.append(row)
            kept += 1
            if kept == needed:
                break
        if kept != needed:
            raise RuntimeError(f"tokenizer support failure {source}/{concept}: {kept} < {needed}")
    return out


def generate_synthetic(seed: int, rows: int, width: int, correlation: float, shared_scale: float,
                       nonlinear: bool, noise_scale: float = 0.05) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    latent = min(8, width // 4)
    q, _ = np.linalg.qr(rng.normal(size=(width, latent * 3)))
    bp, bl, bs = q[:, :latent], q[:, latent:2 * latent], q[:, 2 * latent:3 * latent]
    zp = rng.normal(size=(rows, latent))
    zl = correlation * zp + math.sqrt(max(0.0, 1.0 - correlation**2)) * rng.normal(size=(rows, latent))
    zs = (zp + zl) / math.sqrt(2.0)
    pos, lex, shared = zp @ bp.T, zl @ bl.T, shared_scale * (zs @ bs.T)
    if nonlinear:
        pos, lex, shared = np.tanh(pos), np.tanh(lex), np.tanh(shared)
    noise = noise_scale * rng.normal(size=(rows, width))
    x = pos + lex + shared + noise
    return {k: np.asarray(v, np.float32) for k, v in {"x": x, "position": pos, "lexical": lex, "shared": shared, "noise": noise}.items()}


def train_decomposition(x: np.ndarray, spec: Mapping[str, Any], steps: int, batch_size: int,
                        lr: float, seed: int, device: torch.device,
                        progress: Callable[[int, float], None] | None = None) -> LearnedDecomposition:
    seed_everything(seed)
    multipliers = spec["width_multiplier"] if isinstance(spec["width_multiplier"], list) else [spec["width_multiplier"]]
    topks = spec["topk"]
    model = LearnedDecomposition(x.shape[1], multipliers, topks).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=float(lr))
    xt = torch.from_numpy(np.asarray(x, np.float32)).to(device)
    gen = torch.Generator(device=device).manual_seed(seed)
    for step in range(int(steps)):
        idx = torch.randint(0, len(xt), (min(batch_size, len(xt)),), generator=gen, device=device)
        xb = xt[idx]
        recon, _, _ = model(xb)
        loss = torch.mean((recon - xb) ** 2)
        incoherence_weight = float(spec.get("incoherence_weight", 0.0))
        if len(model.branches) == 2 and incoherence_weight > 0:
            da = nn.functional.normalize(model.branches[0].decoder, dim=1)
            db = nn.functional.normalize(model.branches[1].decoder, dim=1)
            sample = min(128, len(da), len(db))
            ia = torch.randint(0, len(da), (sample,), generator=gen, device=device)
            ib = torch.randint(0, len(db), (sample,), generator=gen, device=device)
            incoherence = torch.mean((da[ia] @ db[ib].T) ** 2)
            loss = loss + incoherence_weight * incoherence
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        model.normalize_decoders()
        if progress and (step == 0 or (step + 1) % 50 == 0):
            progress(step + 1, float(loss.detach().cpu()))
    return model.eval()


@torch.no_grad()
def learned_outputs(model: LearnedDecomposition, x: np.ndarray, device: torch.device) -> tuple[np.ndarray, list[np.ndarray], list[np.ndarray]]:
    xt = torch.from_numpy(np.asarray(x, np.float32)).to(device)
    full, recons, codes = model(xt)
    return (full.cpu().numpy(), [z.cpu().numpy() for z in recons], [z.cpu().numpy() for z in codes])


def orthonormal_rows(matrix: np.ndarray, rank: int) -> np.ndarray:
    if matrix.size == 0:
        return np.zeros((0, matrix.shape[-1]), np.float32)
    _, s, vt = np.linalg.svd(np.asarray(matrix, np.float64), full_matrices=False)
    keep = min(rank, int(np.sum(s > 1e-10)), vt.shape[0])
    return np.asarray(vt[:keep], np.float32)


def linear_basis(method: str, train_x: np.ndarray, base: np.ndarray, cf: np.ndarray, rank: int, seed: int, alpha: float) -> np.ndarray:
    d = train_x.shape[1]
    delta = np.asarray(cf - base, np.float64)
    if method == "pca":
        return orthonormal_rows(train_x - train_x.mean(0), rank)
    if method == "random":
        q, _ = np.linalg.qr(np.random.default_rng(seed).normal(size=(d, rank)))
        return np.asarray(q.T, np.float32)
    if method == "paired_delta_oracle":
        return orthonormal_rows(delta, rank)
    mean_delta = delta.mean(0)
    if method == "task_projection":
        return orthonormal_rows(mean_delta[None, :], 1)
    if method == "linear_erasure":
        xc = np.asarray(train_x - train_x.mean(0), np.float64)
        cov = (xc.T @ xc) / max(1, len(xc))
        direction = np.linalg.solve(cov + float(alpha) * np.eye(d), mean_delta)
        return orthonormal_rows(direction[None, :], 1)
    raise ValueError(method)


def project_component(x: np.ndarray, basis: np.ndarray, center: np.ndarray) -> np.ndarray:
    xc = x - center
    return (xc @ basis.T) @ basis if len(basis) else np.zeros_like(xc)


def ridge_binary_accuracy(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray, test_y: np.ndarray, alpha: float) -> float:
    mu = train_x.mean(0, keepdims=True)
    x = np.asarray(train_x - mu, np.float64)
    z = np.asarray(test_x - mu, np.float64)
    y = np.asarray(train_y, np.float64) * 2.0 - 1.0
    # Stable dual solve; the number of examples is much smaller than hidden width.
    coef = x.T @ np.linalg.solve(x @ x.T + float(alpha) * np.eye(len(x)), y)
    pred = (z @ coef >= 0).astype(np.int64)
    return float(np.mean(pred == np.asarray(test_y, np.int64)))


def _module_for_layer(model: Any, layer: int) -> Any:
    if hasattr(model, "gpt_neox"):
        return model.gpt_neox.layers[layer]
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return model.model.layers[layer]
    if hasattr(model, "transformer") and hasattr(model.transformer, "h"):
        return model.transformer.h[layer]
    raise RuntimeError("unsupported transformer block layout")


@torch.no_grad()
def forward_prompts(model: Any, tokenizer: Any, prompts: Sequence[str], layer: int, batch_size: int,
                    maximum_length: int, device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    hidden, logits = [], []
    for start in range(0, len(prompts), batch_size):
        batch = list(prompts[start:start + batch_size])
        enc = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=maximum_length)
        ids, mask = enc["input_ids"].to(device), enc["attention_mask"].to(device)
        out = model(input_ids=ids, attention_mask=mask, output_hidden_states=True, use_cache=False)
        idx = mask.sum(1) - 1
        ar = torch.arange(len(batch), device=device)
        hidden.append(out.hidden_states[layer + 1][ar, idx].float().cpu().numpy())
        logits.append(out.logits[ar, idx].float().cpu().numpy())
    return np.concatenate(hidden), np.concatenate(logits)


@torch.no_grad()
def patched_logits(model: Any, tokenizer: Any, prompts: Sequence[str], patches: np.ndarray, layer: int,
                   batch_size: int, maximum_length: int, device: torch.device) -> np.ndarray:
    result = []
    module = _module_for_layer(model, layer)
    for start in range(0, len(prompts), batch_size):
        batch = list(prompts[start:start + batch_size])
        patch = torch.from_numpy(np.asarray(patches[start:start + batch_size], np.float32)).to(device)
        enc = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=maximum_length)
        ids, mask = enc["input_ids"].to(device), enc["attention_mask"].to(device)
        idx = mask.sum(1) - 1
        ar = torch.arange(len(batch), device=device)

        def hook(_module: Any, _inputs: Any, output: Any) -> Any:
            h = output[0] if isinstance(output, tuple) else output
            changed = h.clone()
            changed[ar, idx] += patch.to(changed.dtype)
            if isinstance(output, tuple):
                return (changed,) + output[1:]
            return changed

        handle = module.register_forward_hook(hook)
        try:
            out = model(input_ids=ids, attention_mask=mask, use_cache=False)
        finally:
            handle.remove()
        result.append(out.logits[ar, idx].float().cpu().numpy())
    return np.concatenate(result)


def logodds(logits: np.ndarray, rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return np.asarray([logits[i, int(r["answer_cf_id"])] - logits[i, int(r["answer_base_id"])] for i, r in enumerate(rows)], np.float64)


def non_target_kl(base: np.ndarray, patched: np.ndarray, rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    # Normalize after masking the two registered answers, so intended answer movement is not called collateral.
    out = []
    for i, r in enumerate(rows):
        a, b = base[i].astype(np.float64), patched[i].astype(np.float64)
        keep = np.ones(len(a), dtype=bool)
        keep[[int(r["answer_base_id"]), int(r["answer_cf_id"])]] = False
        aa, bb = a[keep], b[keep]
        aa -= np.max(aa); bb -= np.max(bb)
        pa, pb = np.exp(aa), np.exp(bb)
        pa /= pa.sum(); pb /= pb.sum()
        out.append(float(np.sum(pa * (np.log(pa + 1e-300) - np.log(pb + 1e-300)))))
    return np.asarray(out)


def dataset_texts(cfg: Mapping[str, Any], corpus: Mapping[str, Any], seed: int) -> tuple[list[str], str]:
    from datasets import load_dataset
    kwargs = {"split": corpus["split"]}
    if corpus.get("config") is None:
        ds = load_dataset(corpus["dataset"], **kwargs)
    else:
        ds = load_dataset(corpus["dataset"], corpus["config"], **kwargs)
    rng = np.random.default_rng(seed)
    limit = int(cfg["training"]["maximum_text_rows_per_corpus"])
    indices = rng.choice(len(ds), size=min(limit, len(ds)), replace=False)
    texts = []
    for idx in indices:
        row = ds[int(idx)]
        value = "\n".join(str(row.get(f, "")).strip() for f in corpus["text_fields"] if str(row.get(f, "")).strip())
        if value:
            texts.append(value)
    digest = hashlib.sha256(canonical_json(texts)).hexdigest()
    return texts, digest


@torch.no_grad()
def extract_training_activations(model: Any, tokenizer: Any, texts: Sequence[str], layer: int, target_tokens: int,
                                 maximum_length: int, batch_size: int, device: torch.device) -> np.ndarray:
    chunks = []
    count = 0
    for start in range(0, len(texts), batch_size):
        enc = tokenizer(list(texts[start:start + batch_size]), return_tensors="pt", padding=True, truncation=True, max_length=maximum_length)
        ids, mask = enc["input_ids"].to(device), enc["attention_mask"].to(device)
        out = model(input_ids=ids, attention_mask=mask, output_hidden_states=True, use_cache=False)
        valid = mask.bool(); valid[:, 0] = False
        x = out.hidden_states[layer + 1][valid].float().cpu().numpy()
        chunks.append(x); count += len(x)
        if count >= target_tokens:
            break
    if count < target_tokens:
        raise RuntimeError(f"activation support {count} < {target_tokens}")
    return np.concatenate(chunks)[:target_tokens]


def runtime_record(device: torch.device) -> dict[str, Any]:
    rec = {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "torch": torch.__version__,
           "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"), "device": str(device)}
    if device.type == "cuda":
        p = torch.cuda.get_device_properties(0)
        rec.update({"gpu_name": p.name, "gpu_uuid": "GPU-" + str(p.uuid), "gpu_memory": p.total_memory,
                    "cuda": torch.version.cuda})
    return rec


def verify_preservation(cfg: Mapping[str, Any]) -> None:
    if cfg["preservation"].get("v5_authorized") is not False:
        raise RuntimeError("v5 must remain unauthorized")
    for key, row in cfg["preservation"].items():
        if key == "v5_authorized":
            continue
        path = ROOT / row["path"]
        if not path.is_file() or sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"historical preservation failure: {key}")


def candidate_inventory(config_path: Path) -> list[dict[str, Any]]:
    paths = [config_path, PLAN, PLAN_REVIEW, AMENDMENT, SCRIPT, TEST, LAUNCHER, ROOT / "requirements-atlas.lock.txt"]
    out = [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256_file(p), "bytes": p.stat().st_size} for p in paths]
    return sorted(out, key=lambda x: x["path"])


def freeze(config_path: Path) -> None:
    cfg = load_json(config_path); verify_preservation(cfg)
    output = ROOT / cfg["runtime"]["output_root"]
    path = ROOT / cfg["runtime"]["freeze"]
    if output.exists():
        raise RuntimeError("result namespace already exists")
    inv = candidate_inventory(config_path)
    payload = {"schema_version": "proxy_control_benchmark_v1_freeze", "namespace": cfg["namespace"],
               "config_sha256": sha256_file(config_path), "candidate_inventory": inv,
               "candidate_inventory_sha256": hashlib.sha256(canonical_json(inv)).hexdigest(),
               "preservation": cfg["preservation"], "decision_table": cfg["analysis"]["decision_table"],
               "scientific_opening": "FROZEN_BEFORE_MODEL_INFERENCE", "retry_authorized": False}
    exclusive_json(path, payload)
    print(json.dumps(payload, indent=2))


def verify_freeze(config_path: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    verify_preservation(cfg)
    path = ROOT / cfg["runtime"]["freeze"]
    f = load_json(path)
    if f["config_sha256"] != sha256_file(config_path) or f["candidate_inventory"] != candidate_inventory(config_path):
        raise RuntimeError("frozen candidate drift")
    return f


@dataclass
class PanelArrays:
    rows: list[dict[str, Any]]
    base_h: np.ndarray
    cf_h: np.ndarray
    sham_h: np.ndarray
    base_logits: np.ndarray
    cf_logits: np.ndarray
    sham_logits: np.ndarray


def subset_panel(panel: PanelArrays, concept: str, split: str) -> PanelArrays:
    idx = [i for i, r in enumerate(panel.rows) if r["concept"] == concept and r["split"] == split]
    return PanelArrays([panel.rows[i] for i in idx], *(np.asarray(getattr(panel, k))[idx] for k in
        ("base_h", "cf_h", "sham_h", "base_logits", "cf_logits", "sham_logits")))


def panel_forward(model: Any, tokenizer: Any, cfg: Mapping[str, Any], source: str, layer: int, device: torch.device) -> PanelArrays:
    rows = materialize_panel(tokenizer, cfg, source)
    p = cfg["panel"]
    args = (layer, int(p["batch_size"]), int(p["maximum_length"]), device)
    bh, bl = forward_prompts(model, tokenizer, [r["base_prompt"] for r in rows], *args)
    ch, cl = forward_prompts(model, tokenizer, [r["cf_prompt"] for r in rows], *args)
    sh, sl = forward_prompts(model, tokenizer, [r["sham_prompt"] for r in rows], *args)
    return PanelArrays(rows, bh, ch, sh, bl, cl, sl)


def components_for_learned(model: LearnedDecomposition, dev: PanelArrays, ev: PanelArrays, rank: int,
                           device: torch.device) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray], dict[str, Any]]:
    _, db, dcb = learned_outputs(model, dev.base_h, device)
    _, dc, dcc = learned_outputs(model, dev.cf_h, device)
    full_b, eb, ecb = learned_outputs(model, ev.base_h, device)
    full_c, ec, ecc = learned_outputs(model, ev.cf_h, device)
    _, es, _ = learned_outputs(model, ev.sham_h, device)
    if len(model.branches) == 2:
        chosen = assign_k2_branch(dc[0] - db[0], dc[1] - db[1])
        target_b, target_c, target_s = eb[chosen], ec[chosen], es[chosen]
        complement_b, complement_c = eb[1 - chosen], ec[1 - chosen]
        assignment = {"kind": "branch_permutation", "target_branch": chosen, "complement_branch": 1 - chosen}
    else:
        score = np.mean(np.abs(dcc[0] - dcb[0]), axis=0)
        atoms = np.argsort(score)[-min(rank, len(score)):]
        decoder = model.branches[0].decoder.detach().cpu().numpy()
        target_b = ecb[0][:, atoms] @ decoder[atoms]
        target_c = ecc[0][:, atoms] @ decoder[atoms]
        _, _, esc = learned_outputs(model, ev.sham_h, device)
        target_s = esc[0][:, atoms] @ decoder[atoms]
        complement_b, complement_c = full_b - target_b, full_c - target_c
        assignment = {"kind": "source_fitted_atom_selection", "atom_count": len(atoms), "atom_indices": atoms.tolist()}
    return (target_b, target_c, target_s, complement_b, complement_c, full_b), assignment


def evaluate_components(model_lm: Any, tokenizer: Any, cfg: Mapping[str, Any], layer: int, ev: PanelArrays,
                        target_b: np.ndarray, target_c: np.ndarray, target_s: np.ndarray,
                        complement_b: np.ndarray, complement_c: np.ndarray, device: torch.device) -> dict[str, Any]:
    eps = float(cfg["analysis"]["epsilon"])
    full_delta = ev.cf_h - ev.base_h
    delta = target_c - target_b
    sham_delta = target_s - target_b
    full_norm = np.linalg.norm(full_delta, axis=1)
    delta_norm = np.linalg.norm(delta, axis=1)
    sham_full = np.linalg.norm(ev.sham_h - ev.base_h, axis=1)
    capture = delta_norm / np.maximum(full_norm, eps)
    sham_capture = np.linalg.norm(sham_delta, axis=1) / np.maximum(sham_full, eps)
    p = cfg["panel"]
    patched = patched_logits(model_lm, tokenizer, [r["base_prompt"] for r in ev.rows], delta, layer,
                             int(p["batch_size"]), int(p["maximum_length"]), device)
    sham_patched = patched_logits(model_lm, tokenizer, [r["base_prompt"] for r in ev.rows], sham_delta, layer,
                                  int(p["batch_size"]), int(p["maximum_length"]), device)
    erased = patched_logits(model_lm, tokenizer, [r["base_prompt"] for r in ev.rows], -target_b, layer,
                            int(p["batch_size"]), int(p["maximum_length"]), device)
    base_lo, cf_lo = logodds(ev.base_logits, ev.rows), logodds(ev.cf_logits, ev.rows)
    patch_lo, sham_lo, erase_lo = logodds(patched, ev.rows), logodds(sham_patched, ev.rows), logodds(erased, ev.rows)
    full_effect = cf_lo - base_lo
    patch_effect = patch_lo - base_lo
    sham_effect = sham_lo - base_lo
    ratio = delta_norm / np.maximum(full_norm, eps)
    eligible = (np.abs(full_effect) >= float(p["minimum_full_logodds_effect"])) & (ratio <= float(p["maximum_patch_norm_ratio"]))
    recovery = np.where(eligible, patch_effect / np.where(np.abs(full_effect) >= eps, full_effect, np.nan), np.nan)
    behavioral_spec = np.where(eligible, (patch_effect - sham_effect) / np.maximum(np.abs(full_effect), eps), np.nan)
    collateral = non_target_kl(ev.base_logits, patched, ev.rows)
    necessity = erase_lo - base_lo
    return {"representation_capture": capture.tolist(), "sham_capture": sham_capture.tolist(),
            "intervention_specificity_rows": (capture - sham_capture).tolist(),
            "full_logodds_effect": full_effect.tolist(), "patch_logodds_effect": patch_effect.tolist(),
            "sham_logodds_effect": sham_effect.tolist(), "behavioral_recovery_rows": recovery.tolist(),
            "behavioral_specificity_rows": behavioral_spec.tolist(), "necessity_logodds_effect": necessity.tolist(),
            "collateral_kl_rows": collateral.tolist(), "patch_norm_ratio": ratio.tolist(),
            "behavior_eligible": eligible.tolist(), "behavior_eligible_fraction": float(np.mean(eligible)),
            "behavioral_recovery": float(np.nanmedian(recovery)) if np.any(eligible) else float("nan"),
            "behavioral_specificity": float(np.nanmedian(behavioral_spec)) if np.any(eligible) else float("nan"),
            "intervention_specificity": float(np.median(capture - sham_capture)),
            "collateral_kl": float(np.median(collateral)),
            "target_delta": delta, "target_base": target_b, "target_cf": target_c,
            "complement_base": complement_b, "complement_cf": complement_c}


def summarize_method_rows(rows: list[dict[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    smallest = float(cfg["analysis"]["specificity_smallest_effect"])
    draws = int(cfg["analysis"]["bootstrap_draws"])
    out: dict[str, Any] = {}
    for key in ("probe_recovery", "leakage", "selectivity", "intervention_specificity", "behavioral_recovery", "behavioral_specificity", "collateral_kl"):
        vals = [float(r[key]) for r in rows if r.get(key) is not None and np.isfinite(float(r[key]))]
        ci = bootstrap_interval(vals, draws, stable_seed(cfg["seed"], key)) if vals else None
        out[key] = {"n": len(vals), "mean": float(np.mean(vals)) if vals else None, "ci": list(ci) if ci else None,
                    "equivalence": classify_equivalence(ci[0], ci[2], smallest) if ci and key in {"selectivity", "intervention_specificity", "behavioral_specificity"} else None}
    return out


def load_model_and_tokenizer(model_cfg: Mapping[str, Any], device: torch.device) -> tuple[Any, Any]:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_cfg["name"], revision=model_cfg["revision"], local_files_only=True, use_fast=True)
    tokenizer.padding_side = "right"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_cfg["name"], revision=model_cfg["revision"], local_files_only=True,
        torch_dtype=torch.float32, attn_implementation="eager").to(device).eval()
    model.config.use_cache = False
    return model, tokenizer


def worker(config_path: Path, model_key: str, layer: int) -> None:
    cfg = load_json(config_path); freeze_rec = verify_freeze(config_path, cfg)
    model_cfg = next(x for x in cfg["models"] if x["key"] == model_key)
    if layer not in model_cfg["layers"]:
        raise RuntimeError("unregistered layer")
    out = ROOT / cfg["runtime"]["output_root"] / "shards" / f"{model_key}_layer{layer}"
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    seed = stable_seed(cfg["seed"], model_key, layer)
    seed_everything(seed)
    exclusive_json(out / "STARTED.json", {"schema_version": "proxy_control_worker_started_v1", "model": model_key, "layer": layer,
        "seed": seed, "freeze_sha256": sha256_file(ROOT / cfg["runtime"]["freeze"]), "runtime": runtime_record(device)})
    model_lm, tokenizer = load_model_and_tokenizer(model_cfg, device)
    corpus_arrays, corpus_hashes = [], {}
    for corpus in cfg["development_corpora"]:
        texts, digest = dataset_texts(cfg, corpus, stable_seed(seed, corpus["key"]))
        corpus_hashes[corpus["key"]] = {"selected_text_sha256": digest, "rows": len(texts), "cache_fingerprint": corpus["cache_fingerprint"]}
        corpus_arrays.append(extract_training_activations(model_lm, tokenizer, texts, layer,
            int(cfg["training"]["activation_tokens_per_corpus"]), int(cfg["panel"]["maximum_length"]),
            int(cfg["panel"]["batch_size"]), device))
    train_x = np.concatenate(corpus_arrays)
    center = train_x.mean(0)
    scale = float(np.sqrt(np.mean((train_x - center) ** 2)))
    norm_x = np.asarray((train_x - center) / max(scale, 1e-8), np.float32)
    np.savez_compressed(out / "activation_summary.npz", mean=center.astype(np.float32), scale=np.asarray(scale),
                        corpus_mean=np.stack([x.mean(0) for x in corpus_arrays]).astype(np.float32))
    panels = {s: panel_forward(model_lm, tokenizer, cfg, s, layer, device) for s in cfg["controlled_sources"]}
    panel_manifest = {s: {"rows": len(p.rows), "sha256": hashlib.sha256(canonical_json(p.rows)).hexdigest(),
                          "counts": {c: sum(r["concept"] == c for r in p.rows) for c in cfg["concepts"]}} for s, p in panels.items()}
    exclusive_json(out / "PANEL_MANIFEST.json", panel_manifest)
    metric_rows: list[dict[str, Any]] = []
    component_metric_rows: list[dict[str, Any]] = []
    geometry: dict[str, list[np.ndarray]] = {}

    def add_evaluation(method: str, seed_value: int | None, assignment_source: str, concept: str,
                       dev: PanelArrays, ev: PanelArrays, comps: tuple[np.ndarray, ...], recon_fvu: float,
                       sparsity: float, assignment_detail: Mapping[str, Any]) -> None:
        tb, tc, ts, cb, cc, _ = comps
        behavior = evaluate_components(model_lm, tokenizer, cfg, layer, ev, tb, tc, ts, cb, cc, device)
        target_train = np.concatenate([tb, tc]); complement_train = np.concatenate([cb, cc])
        # Evaluation labels are the base/counterfactual states in the held-out source.
        y = np.concatenate([np.zeros(len(tb), dtype=int), np.ones(len(tc), dtype=int)])
        # Cross-source classifiers use the assignment panel's paired states, transformed with the same mapping.
        # The component tuple already reflects the source-fitted mapping; use a deterministic half split to avoid eval-on-train.
        split = max(2, len(y) // 4)
        train_idx = np.r_[0:split, len(tb):len(tb)+split]
        test_idx = np.setdiff1d(np.arange(len(y)), train_idx)
        pr = ridge_binary_accuracy(target_train[train_idx], y[train_idx], target_train[test_idx], y[test_idx], cfg["analysis"]["ridge_alpha"])
        leak = ridge_binary_accuracy(complement_train[train_idx], y[train_idx], complement_train[test_idx], y[test_idx], cfg["analysis"]["ridge_alpha"])
        row = {"schema_version": "proxy_control_metric_v1", "model": model_key, "layer": layer, "model_layer": f"{model_key}:{layer}",
               "method": method, "seed": seed_value, "assignment_source": assignment_source, "evaluation_source": ev.rows[0]["source"],
               "concept": concept, "reconstruction_fvu": recon_fvu, "sparsity": sparsity, "probe_recovery": pr,
               "leakage": leak, "selectivity": pr - leak, "assignment_detail": dict(assignment_detail)}
        for key in ("intervention_specificity", "behavioral_recovery", "behavioral_specificity", "collateral_kl", "behavior_eligible_fraction"):
            value = float(behavior[key])
            row[key] = value if np.isfinite(value) else None
        component_arrays = {
            "intervention_specificity": behavior["intervention_specificity_rows"],
            "behavioral_recovery": behavior["behavioral_recovery_rows"],
            "behavioral_specificity": behavior["behavioral_specificity_rows"],
            "collateral_kl": behavior["collateral_kl_rows"],
        }
        for key, values in component_arrays.items():
            finite = [float(x) for x in values if x is not None and np.isfinite(float(x))]
            ci = bootstrap_interval(finite, int(cfg["analysis"]["bootstrap_draws"]),
                                    stable_seed(cfg["seed"], model_key, layer, method, seed_value, assignment_source, concept, key)) if finite else None
            row[f"{key}_component_ci"] = list(ci) if ci else None
            row[f"{key}_equivalence"] = classify_equivalence(ci[0], ci[2], float(cfg["analysis"]["specificity_smallest_effect"])) if ci and key in {"intervention_specificity", "behavioral_specificity"} else None
        for i, source_row in enumerate(ev.rows):
            rec: dict[str, Any] = {"model": model_key, "layer": layer, "method": method, "seed": seed_value,
                "assignment_source": assignment_source, "evaluation_source": source_row["source"], "concept": concept,
                "component_id": source_row["component_id"], "behavior_eligible": bool(behavior["behavior_eligible"][i])}
            for key, values in component_arrays.items():
                value = float(values[i])
                rec[key] = value if np.isfinite(value) else None
            rec["full_logodds_effect"] = float(behavior["full_logodds_effect"][i])
            rec["patch_norm_ratio"] = float(behavior["patch_norm_ratio"][i])
            component_metric_rows.append(rec)
        row["component_count"] = len(ev.rows)
        metric_rows.append(row)
        geometry.setdefault(f"{method}|{assignment_source}|{concept}", []).append(np.asarray(tb, np.float32))

    # Linear baselines are fitted separately in each transfer direction and concept.
    for assignment_source, evaluation_source in (("SOURCE_A", "SOURCE_B"), ("SOURCE_B", "SOURCE_A")):
        for concept in cfg["concepts"]:
            dev = subset_panel(panels[assignment_source], concept, "development")
            ev = subset_panel(panels[evaluation_source], concept, "test")
            dev_b = (dev.base_h - center) / max(scale, 1e-8); dev_c = (dev.cf_h - center) / max(scale, 1e-8)
            ev_b = (ev.base_h - center) / max(scale, 1e-8); ev_c = (ev.cf_h - center) / max(scale, 1e-8); ev_s = (ev.sham_h - center) / max(scale, 1e-8)
            for method in cfg["linear_methods"]:
                basis = linear_basis(method, norm_x, dev_b, dev_c, int(cfg["analysis"]["rank"]),
                                     stable_seed(seed, method, assignment_source, concept), cfg["analysis"]["ridge_alpha"])
                zero = np.zeros(norm_x.shape[1], np.float32)
                tb, tc, ts = (project_component(z, basis, zero) * scale for z in (ev_b, ev_c, ev_s))
                cb, cc = ev.base_h - center - tb, ev.cf_h - center - tc
                add_evaluation(method, None, assignment_source, concept, dev, ev, (tb, tc, ts, cb, cc, ev.base_h - center),
                               0.0, float(len(basis)), {"kind": "linear_basis", "rank": len(basis)})

    # Learned decompositions share training data and differ only by frozen architecture/seed.
    learned_models: dict[tuple[str, int], LearnedDecomposition] = {}
    for method, spec in cfg["training"]["methods"].items():
        for learned_seed in cfg["training"]["seeds"]:
            job_seed = stable_seed(seed, method, learned_seed)
            atomic_json(out / "HEARTBEAT.json", {"phase": "training", "method": method, "seed": learned_seed, "step": 0})
            mdl = train_decomposition(norm_x, spec, int(cfg["training"]["steps"]), int(cfg["training"]["batch_size"]),
                float(cfg["training"]["learning_rate"]), job_seed, device,
                lambda step, loss, m=method, s=learned_seed: atomic_json(out / "HEARTBEAT.json", {"phase": "training", "method": m, "seed": s, "step": step, "loss": loss}))
            learned_models[(method, int(learned_seed))] = mdl
            with torch.no_grad():
                full, _, codes = mdl(torch.from_numpy(norm_x[:512]).to(device))
                fvu = float(torch.mean((full - torch.from_numpy(norm_x[:512]).to(device)) ** 2).cpu() / torch.var(torch.from_numpy(norm_x[:512])))
                sparsity = float(sum((c != 0).sum(1).float().mean().cpu() for c in codes))
            ckpt = {k: v.detach().cpu().half() for k, v in mdl.state_dict().items()}
            torch.save({"schema_version": "proxy_control_checkpoint_v1", "method": method, "seed": learned_seed,
                        "model": model_key, "layer": layer, "state_dict": ckpt}, out / f"{method}_seed{learned_seed}.pt")
            for assignment_source, evaluation_source in (("SOURCE_A", "SOURCE_B"), ("SOURCE_B", "SOURCE_A")):
                for concept in cfg["concepts"]:
                    dev0 = subset_panel(panels[assignment_source], concept, "development")
                    ev0 = subset_panel(panels[evaluation_source], concept, "test")
                    def norm_panel(pn: PanelArrays) -> PanelArrays:
                        return PanelArrays(pn.rows, *((x - center) / max(scale, 1e-8) for x in
                            (pn.base_h, pn.cf_h, pn.sham_h)), pn.base_logits, pn.cf_logits, pn.sham_logits)
                    devn, evn = norm_panel(dev0), norm_panel(ev0)
                    comps_n, assignment_detail = components_for_learned(mdl, devn, evn, int(cfg["analysis"]["rank"]), device)
                    comps = tuple(z * scale for z in comps_n)
                    # Preserve original logits/rows while components return to activation units.
                    add_evaluation(method, int(learned_seed), assignment_source, concept, dev0, ev0, comps, fvu, sparsity, assignment_detail)

    # Cross-seed/source geometry is descriptive and never substitutes for behavior.
    stability = {}
    for key, reps in geometry.items():
        vals = [centered_cka(reps[i], reps[j]) for i in range(len(reps)) for j in range(i + 1, len(reps))]
        finite = [x for x in vals if np.isfinite(x)]
        stability[key] = {"comparisons": len(vals), "finite_comparisons": len(finite), "mean_cka": float(np.mean(finite)) if finite else None}
    for row in metric_rows:
        key = f"{row['method']}|{row['assignment_source']}|{row['concept']}"
        row["geometric_stability"] = stability[key]["mean_cka"]
    with (out / "metrics.jsonl").open("x") as f:
        for row in metric_rows:
            f.write(canonical_json(row).decode() + "\n")
    with (out / "component_metrics.jsonl").open("x") as f:
        for row in component_metric_rows:
            f.write(canonical_json(row).decode() + "\n")
    summary = {"schema_version": "proxy_control_shard_result_v1", "model": model_key, "layer": layer,
               "rows": len(metric_rows), "corpora": corpus_hashes, "panel_manifest": panel_manifest,
               "stability": stability, "method_summary": summarize_method_rows(metric_rows, cfg),
               "runtime": runtime_record(device), "freeze_sha256": sha256_file(ROOT / cfg["runtime"]["freeze"]),
               "candidate_inventory_sha256": freeze_rec["candidate_inventory_sha256"]}
    exclusive_json(out / "result.json", summary)
    exclusive_json(out / "COMPLETE.json", {"status": "COMPLETE", "result_sha256": sha256_file(out / "result.json"),
        "metrics_sha256": sha256_file(out / "metrics.jsonl"), "component_metrics_sha256": sha256_file(out / "component_metrics.jsonl"),
        "component_metric_rows": len(component_metric_rows), "training_run": True})


def synthetic_job(config_path: Path) -> None:
    cfg = load_json(config_path); freeze_rec = verify_freeze(config_path, cfg)
    out = ROOT / cfg["runtime"]["output_root"] / "synthetic"
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    exclusive_json(out / "STARTED.json", {"schema_version": "proxy_control_synthetic_started_v1", "runtime": runtime_record(device),
        "freeze_sha256": sha256_file(ROOT / cfg["runtime"]["freeze"])})
    rows = []
    sc = cfg["synthetic"]
    for corr in sc["correlations"]:
        for shared in sc["shared_scales"]:
            for nonlinear in sc["nonlinear"]:
                # Generate once and split so train/test share the exact latent bases while rows remain disjoint.
                n_train, n_test = int(sc["rows"]), int(sc["test_rows"])
                all_data = generate_synthetic(stable_seed(cfg["seed"], corr, shared, nonlinear), n_train + n_test,
                                              int(sc["width"]), corr, shared, nonlinear, sc["noise_scale"])
                train = {k: v[:n_train] for k, v in all_data.items()}
                test = {k: v[n_train:] for k, v in all_data.items()}
                for method, spec in cfg["training"]["methods"].items():
                    for s in cfg["training"]["seeds"]:
                        atomic_json(out / "HEARTBEAT.json", {"correlation": corr, "shared": shared, "nonlinear": nonlinear, "method": method, "seed": s})
                        mdl = train_decomposition(train["x"], spec, int(sc["training_steps"]), int(cfg["training"]["batch_size"]),
                            float(cfg["training"]["learning_rate"]), stable_seed(cfg["seed"], method, s, corr, shared, nonlinear), device)
                        full, branches, codes = learned_outputs(mdl, test["x"], device)
                        if len(branches) == 2:
                            chosen = 0 if centered_cka(branches[0], test["position"]) >= centered_cka(branches[1], test["position"]) else 1
                            target, other = branches[chosen], branches[1 - chosen]
                        else:
                            score = np.abs(np.corrcoef(codes[0].T, test["position"][:, 0], rowvar=True)[:-1, -1])
                            atoms = np.argsort(np.nan_to_num(score))[-int(cfg["analysis"]["rank"]):]
                            decoder = mdl.branches[0].decoder.detach().cpu().numpy()
                            target = codes[0][:, atoms] @ decoder[atoms]; other = full - target
                        row = {"correlation": corr, "shared_scale": shared, "nonlinear": nonlinear, "method": method, "seed": s,
                            "reconstruction_fvu": float(np.mean((full - test["x"])**2) / max(np.var(test["x"]), 1e-8)),
                            "position_cka": centered_cka(target, test["position"]), "position_leakage_cka": centered_cka(other, test["position"]),
                            "lexical_cka": centered_cka(other, test["lexical"]), "lexical_leakage_cka": centered_cka(target, test["lexical"]),
                            "shared_target_cka": centered_cka(target, test["shared"]), "shared_other_cka": centered_cka(other, test["shared"]),
                            "active_budget": float(sum(np.mean(np.count_nonzero(c, axis=1)) for c in codes))}
                        rows.append({k: (float(v) if isinstance(v, (float, np.floating)) and np.isfinite(v) else None)
                                     if isinstance(v, (float, np.floating)) else v for k, v in row.items()})
    with (out / "metrics.jsonl").open("x") as f:
        for row in rows:
            f.write(canonical_json(row).decode() + "\n")
    result = {"schema_version": "proxy_control_synthetic_result_v1", "rows": len(rows),
              "finite_or_explicit_missing": bool(all(v is None or np.isfinite(v) for r in rows for v in r.values() if isinstance(v, float) or v is None)),
              "freeze_sha256": sha256_file(ROOT / cfg["runtime"]["freeze"]), "candidate_inventory_sha256": freeze_rec["candidate_inventory_sha256"]}
    exclusive_json(out / "result.json", result)
    exclusive_json(out / "COMPLETE.json", {"status": "COMPLETE", "result_sha256": sha256_file(out / "result.json"), "metrics_sha256": sha256_file(out / "metrics.jsonl")})


def aggregate(config_path: Path) -> None:
    cfg = load_json(config_path); verify_freeze(config_path, cfg)
    root = ROOT / cfg["runtime"]["output_root"]
    out = root / "aggregate"
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    exclusive_json(out / "STARTED.json", {"schema_version": "proxy_control_aggregate_started_v1", "waiting": True})
    expected = [(m["key"], l) for m in cfg["models"] for l in m["layers"]]
    paths = [root / "shards" / f"{m}_layer{l}" / "COMPLETE.json" for m, l in expected] + [root / "synthetic" / "COMPLETE.json"]
    while not all(p.is_file() for p in paths):
        atomic_json(out / "HEARTBEAT.json", {"waiting_for": [p.relative_to(root).as_posix() for p in paths if not p.is_file()]})
        time.sleep(60)
    metrics = []
    for model_key, layer in expected:
        p = root / "shards" / f"{model_key}_layer{layer}" / "metrics.jsonl"
        metrics.extend(json.loads(line) for line in p.read_text().splitlines() if line)
    from scipy.stats import spearmanr
    associations = []
    proxies = {"reconstruction_quality": lambda r: -r["reconstruction_fvu"], "sparsity": lambda r: -r["sparsity"],
               "probe_recovery": lambda r: r["probe_recovery"], "geometric_stability": lambda r: r["geometric_stability"]}
    controls = {"selectivity": lambda r: r["selectivity"], "intervention_specificity": lambda r: r["intervention_specificity"],
                "behavioral_recovery": lambda r: r["behavioral_recovery"], "behavioral_specificity": lambda r: r["behavioral_specificity"],
                "collateral_safety": lambda r: -r["collateral_kl"]}
    clusters = sorted({r["model_layer"] for r in metrics})
    rng = np.random.default_rng(stable_seed(cfg["seed"], "aggregate"))
    def finite_value(fn: Callable[[Mapping[str, Any]], Any], row: Mapping[str, Any]) -> bool:
        try:
            value = fn(row)
            return value is not None and bool(np.isfinite(float(value)))
        except (TypeError, ValueError):
            return False
    for pn, pf in proxies.items():
        for cn, cf in controls.items():
            pairs = [(float(pf(r)), float(cf(r)), r["model_layer"]) for r in metrics if finite_value(pf, r) and finite_value(cf, r)]
            rho = float(spearmanr([x[0] for x in pairs], [x[1] for x in pairs]).statistic) if len(pairs) >= 3 else float("nan")
            boots = []
            for _ in range(int(cfg["analysis"]["bootstrap_draws"])):
                chosen = rng.choice(clusters, len(clusters), replace=True)
                sample = [x for c in chosen for x in pairs if x[2] == c]
                if len(sample) >= 3:
                    boots.append(float(spearmanr([x[0] for x in sample], [x[1] for x in sample]).statistic))
            ci = np.quantile(np.asarray(boots)[np.isfinite(boots)], [0.025, 0.5, 0.975]).tolist() if np.isfinite(boots).any() else [None] * 3
            associations.append({"proxy": pn, "control": cn, "rho": rho, "cluster_bootstrap_ci": ci, "rows": len(pairs), "clusters": len(clusters)})
    result = {"schema_version": "proxy_control_aggregate_result_v1", "status": "EXPLORATORY_COMPLETE_REQUIRES_CLAIM_REVIEW",
              "metric_rows": len(metrics), "model_layer_clusters": len(clusters), "associations": associations,
              "decision_table_frozen": cfg["analysis"]["decision_table"], "no_automatic_claim": True}
    exclusive_json(out / "result.json", result)
    exclusive_json(out / "COMPLETE.json", {"status": "COMPLETE", "result_sha256": sha256_file(out / "result.json")})


def smoke(config_path: Path, output: Path) -> None:
    cfg = load_json(config_path)
    if output.exists():
        raise FileExistsError(output)
    seed_everything(int(cfg["seed"]))
    specs = make_controlled_specs(int(cfg["seed"]), "SOURCE_A", 4)
    d = generate_synthetic(3, 64, 16, 0.5, 0.4, False)
    dev = torch.device("cpu")
    spec = {"width_multiplier": [1, 1], "topk": [2, 2]}
    mdl = train_decomposition(d["x"], spec, 2, 16, 1e-3, 7, dev)
    full, branches, codes = learned_outputs(mdl, d["x"], dev)
    result = {"schema_version": "proxy_control_smoke_v1", "spec_sha256": hashlib.sha256(canonical_json(specs)).hexdigest(),
              "rows": len(specs), "finite": bool(np.isfinite(full).all()), "active": [float(np.mean(np.count_nonzero(c, axis=1))) for c in codes],
              "cka": centered_cka(branches[0], branches[0]), "interval": list(bootstrap_interval(np.arange(10), 20, 4))}
    exclusive_json(output, result)


def status(config_path: Path) -> None:
    cfg = load_json(config_path); root = ROOT / cfg["runtime"]["output_root"]
    rows = []
    for m in cfg["models"]:
        for layer in m["layers"]:
            p = root / "shards" / f"{m['key']}_layer{layer}"
            rows.append({"job": f"{m['key']}_layer{layer}", "started": (p / "STARTED.json").is_file(), "complete": (p / "COMPLETE.json").is_file(),
                         "heartbeat": load_json(p / "HEARTBEAT.json") if (p / "HEARTBEAT.json").is_file() else None})
    p = root / "synthetic"; rows.append({"job": "synthetic", "started": (p / "STARTED.json").is_file(), "complete": (p / "COMPLETE.json").is_file(),
                                         "heartbeat": load_json(p / "HEARTBEAT.json") if (p / "HEARTBEAT.json").is_file() else None})
    print(json.dumps(rows, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["freeze", "smoke", "worker", "synthetic", "aggregate", "status"])
    ap.add_argument("--config", default="configs/proxy_control_benchmark_v1/run.json")
    ap.add_argument("--output")
    ap.add_argument("--model")
    ap.add_argument("--layer", type=int)
    args = ap.parse_args()
    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config)
    if args.command == "freeze": freeze(config_path)
    elif args.command == "smoke": smoke(config_path, (ROOT / args.output).resolve())
    elif args.command == "worker":
        if args.model is None or args.layer is None: ap.error("worker requires --model and --layer")
        worker(config_path, args.model, args.layer)
    elif args.command == "synthetic": synthetic_job(config_path)
    elif args.command == "aggregate": aggregate(config_path)
    else: status(config_path)


if __name__ == "__main__":
    main()
