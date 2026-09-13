#!/usr/bin/env python3
"""
Self-contained downloader for the local/heterogeneous model pair used in the
ExtAgents paper (Liu et al., ACL 2026).

Models
------
- Reasoning Agent : meta-llama/Llama-3.1-8B-Instruct
- Seeking Agent   : meta-llama/Llama-3.2-3B-Instruct

The paper reports homogeneous results with Llama-3.1-8B-Instruct for both
roles, and a heterogeneous speed/accuracy trade-off using Llama-3.2-3B-Instruct
for Seeking Agents and Llama-3.1-8B-Instruct for the Reasoning Agent
(Section 5.2, Table 6).

Hugging Face access
-------------------
Llama weights are gated. Before running this script you must:
1. Create/own a Hugging Face account.
2. Accept the license for each model page:
   https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
   https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
3. Create a read token at https://huggingface.co/settings/tokens
4. Either export HF_TOKEN=<token> or pass --token <token> below.

Usage
-----
    # Download both models to ./models
    python scripts/download_local_models.py --models all

    # Download only the reasoner
    python scripts/download_local_models.py --models reasoner --cache-dir ./models

    # Use an explicit token
    python scripts/download_local_models.py --models all --token hf_xxx

Hardware note
-------------
This script only downloads weights. Running the models on a Tesla V100 with
CUDA 11.2 requires special care: the repository pins torch==2.7.0, which needs
CUDA >= 11.8 (and a driver >= 520). Driver 460.91.03 supports only up to
CUDA 11.4, so GPU inference with the stock PyTorch wheel will fail. Options:
    1. Upgrade the NVIDIA driver + CUDA toolkit (requires admin rights).
    2. Run inference on CPU (very slow for 8B parameters).
    3. Use llama.cpp / ollama compiled for your CUDA/driver combo.
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import snapshot_download
except ImportError as exc:  # pragma: no cover - utility script
    raise ImportError(
        "huggingface_hub is required. Install with:\n"
        "    pip install huggingface_hub>=0.20.0"
    ) from exc


REASONER = "meta-llama/Llama-3.1-8B-Instruct"
SEEKER = "meta-llama/Llama-3.2-3B-Instruct"

MODEL_CHOICES = {
    "all": [REASONER, SEEKER],
    "reasoner": [REASONER],
    "seeker": [SEEKER],
    "both_8b": [REASONER],          # homogeneous: use 8B for both roles
    "both_3b": [SEEKER],            # homogeneous: use 3B for both roles
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download ExtAgents local model weights from Hugging Face."
    )
    parser.add_argument(
        "--models",
        type=str,
        default="all",
        choices=list(MODEL_CHOICES.keys()),
        help=(
            "Which weights to fetch. 'reasoner' = Llama-3.1-8B-Instruct, "
            "'seeker' = Llama-3.2-3B-Instruct, 'all' = both."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="./models",
        help="Local directory where downloaded weights are materialized.",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("HF_TOKEN"),
        help=(
            "Hugging Face read token. Defaults to the HF_TOKEN environment "
            "variable."
        ),
    )
    return parser.parse_args()


def download_model(repo_id: str, cache_dir: Path, token: str | None) -> Path:
    """Download a single model into cache_dir/repo-id."""
    local_dir = cache_dir / repo_id.replace("/", "--")
    local_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[download] {repo_id}")
    print(f"[download] destination: {local_dir.resolve()}")

    snapshot_download(
        repo_id=repo_id,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        token=token,
        resume_download=True,
    )

    print(f"[download] completed: {local_dir.resolve()}")
    return local_dir


def main() -> int:
    args = parse_args()

    if not args.token:
        print(
            "ERROR: No Hugging Face token provided. Set HF_TOKEN or pass --token.\n"
            "The Llama model pages must also be accepted in your Hugging Face account.",
            file=sys.stderr,
        )
        return 1

    cache_dir = Path(args.cache_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    repo_ids = MODEL_CHOICES[args.models]
    print(f"Will download {len(repo_ids)} model(s) to {cache_dir}")

    downloaded = []
    for repo_id in repo_ids:
        try:
            downloaded.append(download_model(repo_id, cache_dir, args.token))
        except Exception as exc:  # pragma: no cover - utility script
            print(f"ERROR downloading {repo_id}: {exc}", file=sys.stderr)
            return 1

    print("\n[done] Downloaded models:")
    for path in downloaded:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
