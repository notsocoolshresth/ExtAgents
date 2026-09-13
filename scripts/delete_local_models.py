#!/usr/bin/env python3
"""
Delete local ExtAgents model weights downloaded by download_local_models.py.

This removes only the weights materialized into --cache-dir (default ./models).
It does NOT purge the global Hugging Face cache under ~/.cache/huggingface or
HF_HOME by default; pass --include-hf-cache to do so as well.

Usage
-----
    python scripts/delete_local_models.py --models all
    python scripts/delete_local_models.py --models reasoner
    python scripts/delete_local_models.py --models all --include-hf-cache
"""

import argparse
import shutil
import sys
from pathlib import Path


REASONER = "meta-llama/Llama-3.1-8B-Instruct"
SEEKER = "meta-llama/Llama-3.2-3B-Instruct"

MODEL_CHOICES = {
    "all": [REASONER, SEEKER],
    "reasoner": [REASONER],
    "seeker": [SEEKER],
    "both_8b": [REASONER],
    "both_3b": [SEEKER],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete downloaded ExtAgents local model weights."
    )
    parser.add_argument(
        "--models",
        type=str,
        default="all",
        choices=list(MODEL_CHOICES.keys()),
        help="Which weights to remove.",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="./models",
        help="Directory where weights were materialized by download_local_models.py.",
    )
    parser.add_argument(
        "--include-hf-cache",
        action="store_true",
        help=(
            "Also remove the matching repositories from the global Hugging Face "
            "cache (HF_HOME/hub)."
        ),
    )
    return parser.parse_args()


def freed_mb(path: Path) -> float:
    """Return total size of a directory tree in MiB."""
    total = 0
    if not path.exists():
        return 0.0
    for entry in path.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total / (1024 * 1024)


def delete_local(repo_id: str, cache_dir: Path) -> float:
    """Delete the materialized local copy and return MiB freed."""
    local_dir = cache_dir / repo_id.replace("/", "--")
    if not local_dir.exists():
        print(f"[local] not found: {local_dir}")
        return 0.0

    size = freed_mb(local_dir)
    shutil.rmtree(local_dir)
    print(f"[local] deleted {local_dir} ({size:.1f} MiB)")
    return size


def delete_hf_cache(repo_id: str) -> float:
    """Delete matching snapshots from the global HF cache and return MiB freed."""
    from huggingface_hub import constants

    hf_cache = Path(constants.HF_HUB_CACHE)
    repo_name = repo_id.replace("/", "--")
    repo_dir = hf_cache / repo_name

    if not repo_dir.exists():
        print(f"[hf-cache] not found: {repo_dir}")
        return 0.0

    size = freed_mb(repo_dir)
    shutil.rmtree(repo_dir)
    print(f"[hf-cache] deleted {repo_dir} ({size:.1f} MiB)")
    return size


def main() -> int:
    args = parse_args()
    cache_dir = Path(args.cache_dir).resolve()

    repo_ids = MODEL_CHOICES[args.models]
    print(f"Will remove {len(repo_ids)} model(s)")

    total_freed = 0.0
    for repo_id in repo_ids:
        total_freed += delete_local(repo_id, cache_dir)
        if args.include_hf_cache:
            try:
                total_freed += delete_hf_cache(repo_id)
            except Exception as exc:  # pragma: no cover - utility script
                print(
                    f"ERROR removing HF cache for {repo_id}: {exc}",
                    file=sys.stderr,
                )

    print(f"\n[done] Total space freed: {total_freed:.1f} MiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
