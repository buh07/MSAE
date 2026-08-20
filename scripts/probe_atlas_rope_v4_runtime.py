#!/usr/bin/env python3
"""No-weight/no-forward runtime probe for Atlas v3.4 attempt 8."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import platform
import sys
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_rope_v4 import ROOT, atomic_json, loaded_library_attestation, sha256_file


EXPECTED_SOURCE_HASHES = {
    "modeling_gpt_neox.py": "8747c839bf7a3bceb05d7f80aad62a67cb83f95cb4ad0535f76eab6c83a84a54",
    "GPTNeoXAttention": "46a09756ea4c6804a205ec754f4fbf7f6df47b819d199006c6024990d0b01b0e",
    "GPTNeoXRotaryEmbedding": "b8650f86b61c6f7ca0b8b692e7d40e08a9be37bbf70724812036ea13ba40080e",
    "apply_rotary_pos_emb": "473b44bd10c3afd9bb8eb2bd7d383b4848606f44dd9c958225d65e8df63d5503",
    "rotate_half": "f714a4b1160c694e270d9191a9f133e53856e2a1c62f5cd2f85740f7c2692397",
    "_autoset_attn_implementation": "574b00831199f419a24669d08d9bbd16d239024f2c979d03085df3a2ccbe56fb",
    "sdpa_attention_forward": "601d992611ca2f1854db8559f146f7b4165af30456e2a686c9f1e741eb77e04b",
}


def _gpu_uuid(index: int) -> str:
    value = str(torch.cuda.get_device_properties(index).uuid)
    return value if value.startswith("GPU-") else f"GPU-{value}"


def _loaded_paths() -> list[Path]:
    prefixes = ("libtorch", "libcuda", "libcud", "libcublas")
    paths = {Path(torch._C.__file__).resolve()}
    for line in Path("/proc/self/maps").read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields:
            continue
        raw = fields[-1]
        if not raw.startswith("/"):
            continue
        path = Path(raw)
        name = path.name.lower()
        if name.startswith(prefixes):
            paths.add(path.resolve())
    return sorted(paths, key=lambda path: str(path).encode("utf-8"))


def _source_hashes() -> tuple[str, dict[str, str]]:
    import transformers
    from transformers.modeling_utils import PreTrainedModel
    from transformers.models.gpt_neox import modeling_gpt_neox as modeling
    try:
        from transformers.integrations.sdpa_attention import sdpa_attention_forward
    except ImportError:
        from transformers.modeling_utils import ALL_ATTENTION_FUNCTIONS
        sdpa_attention_forward = ALL_ATTENTION_FUNCTIONS["sdpa"]

    values = {
        "modeling_gpt_neox.py": sha256_file(Path(modeling.__file__)),
        "GPTNeoXAttention": hashlib.sha256(inspect.getsource(modeling.GPTNeoXAttention).encode()).hexdigest(),
        "GPTNeoXRotaryEmbedding": hashlib.sha256(inspect.getsource(modeling.GPTNeoXRotaryEmbedding).encode()).hexdigest(),
        "apply_rotary_pos_emb": hashlib.sha256(inspect.getsource(modeling.apply_rotary_pos_emb).encode()).hexdigest(),
        "rotate_half": hashlib.sha256(inspect.getsource(modeling.rotate_half).encode()).hexdigest(),
        "_autoset_attn_implementation": hashlib.sha256(inspect.getsource(PreTrainedModel._autoset_attn_implementation).encode()).hexdigest(),
        "sdpa_attention_forward": hashlib.sha256(inspect.getsource(sdpa_attention_forward).encode()).hexdigest(),
    }
    return transformers.__version__, values


def probe(output: Path) -> dict[str, object]:
    if output.exists():
        raise RuntimeError(f"create-once runtime probe already exists: {output}")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    torch.cuda.init()
    # Runtime allocation only: no weights and no neural forward.
    allocation = torch.empty(1, dtype=torch.float32, device="cuda:0")
    torch.cuda.synchronize(0)
    del allocation
    required_libraries = loaded_library_attestation(_loaded_paths())
    transformers_version, source_hashes = _source_hashes()
    if source_hashes != EXPECTED_SOURCE_HASHES:
        raise RuntimeError(f"pinned Transformers source hash drift: {source_hashes}")
    flags = {
        "flash": torch.backends.cuda.flash_sdp_enabled(),
        "mem_efficient": torch.backends.cuda.mem_efficient_sdp_enabled(),
        "math": torch.backends.cuda.math_sdp_enabled(),
        "cudnn": torch.backends.cuda.cudnn_sdp_enabled(),
    }
    payload: dict[str, object] = {
        "schema_version": "atlas_rope_v4_attempt8_runtime_probe_v1",
        "status": "PASS_NO_WEIGHT_NO_FORWARD",
        "python": platform.python_version(),
        "executable": str(Path(sys.executable).resolve()),
        "torch": torch.__version__,
        "transformers": transformers_version,
        "cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "gpu_uuid": _gpu_uuid(0),
        "gpu_name": torch.cuda.get_device_name(0),
        "sdpa_flags": flags,
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "torch_C": {"path": str(Path(torch._C.__file__).resolve()), "sha256": sha256_file(Path(torch._C.__file__))},
        "required_libraries": required_libraries,
        "source_hashes": source_hashes,
        "model_weights_loaded": False,
        "neural_forward_run": False,
        "neural_training_run": False,
    }
    expected = {
        "torch": "2.7.0", "transformers": "4.53.2", "cuda": "12.8", "cudnn": 90800,
        "gpu_uuid": "GPU-ec526219-fb07-e57e-a30d-5d2ab843fb15",
        "cublas_workspace_config": ":4096:8",
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise RuntimeError(f"runtime probe drift {key}: {payload[key]} != {value}")
    if flags != {"flash": True, "mem_efficient": True, "math": True, "cudnn": True}:
        raise RuntimeError(f"SDPA flags drift: {flags}")
    atomic_json(output, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data/atlas_rope_v4_attempt8_runtime_probe.json")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    print(json.dumps(probe(output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
