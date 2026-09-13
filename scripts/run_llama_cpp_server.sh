#!/usr/bin/env bash
#
# Start a llama.cpp OpenAI-compatible server for one ExtAgents role.
#
# This assumes you have already:
#   1. Run scripts/setup_llama_cpp_cuda114.sh
#   2. Sourced ./activate_llama_cpp_cuda114.sh
#   3. Run python scripts/download_gguf_models.py --models all
#
# Usage:
#   # Reasoner on port 8001
#   bash scripts/run_llama_cpp_server.sh --model reasoner --port 8001
#
#   # Seeker on port 8002 (run in a second terminal/screen/tmux session)
#   bash scripts/run_llama_cpp_server.sh --model seeker --port 8002
#
#   # Custom GPU split across the 4 V100s
#   bash scripts/run_llama_cpp_server.sh --model reasoner --port 8001 --tensor-split "8,8,8,8"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODEL="reasoner"
PORT="8001"
N_GPU_LAYERS="999"
TENSOR_SPLIT=""
CTX_SIZE="131072"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --model {reasoner|seeker}   Which GGUF model to serve (default: reasoner)
  --port PORT                 HTTP port (default: 8001)
  --n-gpu-layers N            Number of layers to offload (default: 999 = all)
  --tensor-split "a,b,c,d"    Split tensors across GPUs (MiB ratios)
  --ctx-size N                Context size in tokens (default: 131072)
  -h, --help                  Show this message
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        --n-gpu-layers) N_GPU_LAYERS="$2"; shift 2 ;;
        --tensor-split) TENSOR_SPLIT="$2"; shift 2 ;;
        --ctx-size) CTX_SIZE="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

if [[ -z "${LLAMA_CPP_DIR:-}" ]]; then
    LLAMA_CPP_DIR="${REPO_ROOT}/.llama_cpp"
fi

SERVER="${LLAMA_CPP_DIR}/build/bin/llama-server"
if [[ ! -x "${SERVER}" ]]; then
    echo "ERROR: llama-server not found at ${SERVER}" >&2
    echo "Run: bash scripts/setup_llama_cpp_cuda114.sh" >&2
    exit 1
fi

# Locate the GGUF file from the manifest or by glob.
GGUF_DIR="${REPO_ROOT}/models-gguf"
MANIFEST="${GGUF_DIR}/gguf_manifest.txt"

GGUF_FILE=""
if [[ -f "${MANIFEST}" ]]; then
    GGUF_FILE="$(grep "^${MODEL}=" "${MANIFEST}" | head -n1 | cut -d= -f2-)"
fi

if [[ -z "${GGUF_FILE}" || ! -f "${GGUF_FILE}" ]]; then
    # Fallback: glob in the GGUF dir
    GGUF_FILE="$(find "${GGUF_DIR}" -maxdepth 1 -type f -iname "*${MODEL}*.gguf" | head -n1)"
fi

if [[ -z "${GGUF_FILE}" || ! -f "${GGUF_FILE}" ]]; then
    echo "ERROR: No GGUF file found for role '${MODEL}' in ${GGUF_DIR}" >&2
    echo "Run: python scripts/download_gguf_models.py --models ${MODEL}" >&2
    exit 1
fi

echo "[server] role : ${MODEL}"
echo "[server] file : ${GGUF_FILE}"
echo "[server] port : ${PORT}"
echo "[server] ctx  : ${CTX_SIZE}"
echo "[server] binary: ${SERVER}"
echo ""

# Build the argument list.
ARGS=(
    "--model" "${GGUF_FILE}"
    "--port" "${PORT}"
    "--host" "0.0.0.0"
    "--n-gpu-layers" "${N_GPU_LAYERS}"
    "--ctx-size" "${CTX_SIZE}"
    "--parallel" "1"
    "--batch-size" "1024"
    "--ubatch-size" "1024"
)

if [[ -n "${TENSOR_SPLIT}" ]]; then
    ARGS+=("--tensor-split" "${TENSOR_SPLIT}")
fi

# Run.
exec "${SERVER}" "${ARGS[@]}"
