#!/usr/bin/env python3
"""
Download quantized GGUF versions of the ExtAgents local model pair.

Why GGUF?
---------
Your system has CUDA 11.2 / driver 460, which cannot run PyTorch 2.x GPU
wheels. llama.cpp compiled with CUDA 11.4 can run GGUF models on the V100s
without root access.

Default sources (ungated, reliable):
  - Reasoner : bartowski/Llama-3.1-8B-Instruct-GGUF
  - Seeker   : bartowski/Llama-3.2-3B-Instruct-GGUF

Quantization
------------
  - Q4_K_M : fastest, smallest (~4.9 GB for 8B, ~2 GB for 3B). Good quality.
  - Q5_K_M : better quality, slightly larger/slower.
  - Q6_K   : very close to FP16, noticeably slower.

For research reproduction, Q5_K_M is a reasonable balance; Q4_K_M if you are
GPU-memory constrained (you are not — each V100 has 32 GB).

Usage
-----
    source ./activate_llama_cpp_cuda114.sh
    python scripts/download_gguf_models.py --models all --quant Q5_K_M

    python scripts/download_gguf_models.py --models reasoner --quant Q4_K_M
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from huggingface_hub import hf_hub_download
except ImportError as exc:  # pragma: no cover - utility script
    raise ImportError(
        "huggingface_hub is required. Install with:\n"
        "    pip install huggingface_hub>=0.20.0"
    ) from exc


REASONER_REPO = "bartowski/Llama-3.1-8B-Instruct-GGUF"
SEEKER_REPO = "bartowski/Llama-3.2-3B-Instruct-GGUF"

MODEL_CHOICES = {
    "all": [("reasoner", REASONER_REPO), ("seeker", SEEKER_REPO)],
    "reasoner": [("reasoner", REASONER_REPO)],
    "seeker": [("seeker", SEEKER_REPO)],
    "both_8b": [("reasoner", REASONER_REPO)],
    "both_3b": [("seeker", SEEKER_REPO)],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download GGUF versions of the ExtAgents local models."
    )
    parser.add_argument(
        "--models",
        type=str,
        default="all",
        choices=list(MODEL_CHOICES.keys()),
        help="Which models to download.",
    )
    parser.add_argument(
        "--quant",
        type=str,
        default="Q5_K_M",
        choices=["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"],
        help="GGUF quantization level.",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="./models-gguf",
        help="Directory to store the .gguf files.",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("HF_TOKEN"),
        help="Optional Hugging Face token (not required for ungated GGUF repos).",
    )
    return parser.parse_args()


def find_gguf_filename(repo_id: str, quant: str) -> str:
    """List remote files and pick the one matching the requested quant."""
    from huggingface_hub import list_repo_files

    pattern = re.compile(rf"^(?:.*[-_])?{re.escape(quant)}\.gguf$")
    candidates = []
    for fname in list_repo_files(repo_id, token=os.environ.get("HF_TOKEN")):
        if pattern.match(fname):
            candidates.append(fname)

    if not candidates:
        raise RuntimeError(
            f"No {quant} GGUF file found in {repo_id}. "
            f"Try a different --quant value."
        )
    # Prefer the shortest filename; often the plain model name without extra suffixes.
    candidates.sort(key=len)
    return candidates[0]


def download_gguf(role: str, repo_id: str, quant: str, cache_dir: Path, token: str | None) -> Path:
    filename = find_gguf_filename(repo_id, quant)
    print(f"\n[download] {role}: {repo_id}/{filename}")

    local_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=str(cache_dir),
        local_dir_use_symlinks=False,
        token=token,
        resume_download=True,
    )

    print(f"[download] saved: {local_path}")
    return Path(local_path)


def main() -> int:
    args = parse_args()
    cache_dir = Path(args.cache_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    models = MODEL_CHOICES[args.models]
    print(f"Will download {len(models)} GGUF model(s) to {cache_dir}")

    downloaded = {}
    for role, repo_id in models:
        try:
            downloaded[role] = download_gguf(role, repo_id, args.quant, cache_dir, args.token)
        except Exception as exc:  # pragma: no cover - utility script
            print(f"ERROR downloading {role}: {exc}", file=sys.stderr)
            return 1

    # Write a small manifest so the launcher script can find the files.
    manifest = cache_dir / "gguf_manifest.txt"
    with manifest.open("w") as f:
        for role, path in downloaded.items():
            f.write(f"{role}={path}\n")

    print("\n[done] Downloaded:")
    for role, path in downloaded.items():
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  {role:8s} {path.name} ({size_mb:.1f} MiB)")
    print(f"\nManifest written to: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
