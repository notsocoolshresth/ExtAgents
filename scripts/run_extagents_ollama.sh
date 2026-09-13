#!/usr/bin/env bash
#
# Run ExtAgents against a local Ollama server.
#
# This uses the paper's homogeneous local model: Llama-3.1-8B-Instruct
# (Ollama tag: llama3.1:8b) for both Seeking and Reasoning roles.
#
# Requirements:
#   - Ollama server running:  ollama serve
#   - Model pulled:           ollama pull llama3.1:8b
#
# Usage:
#   # Default RAG task with the paper's local model
#   bash scripts/run_extagents_ollama.sh
#
#   # InfiniteBench En.QA task
#   bash scripts/run_extagents_ollama.sh --task en --output_dir results_en
#
#   # Custom chunker experiment
#   bash scripts/run_extagents_ollama.sh --chunker recursive_paragraph

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Defaults matching the paper's local baseline
TASK="rag"
OUTPUT_DIR="results_rag_ollama"
CHUNK_LENGTH=8000
INPUT_LENGTH=128000
CONTEXT_LENGTH=32768
MODEL="llama3.1:8b"
NUM_WORKERS=1
CHUNKER="legacy"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --task {rag|en|zh}          Task to run (default: rag)
  --output_dir DIR            Output directory (default: results_rag_ollama)
  --chunk_length N            Chunk size in tokens (default: 8000)
  --input_length N            Total input length in tokens (default: 128000)
  --context_length N          Model context length (default: 32768)
  --model MODEL               Ollama model tag (default: llama3.1:8b)
  --num_workers N             Parallel workers (default: 1)
  --chunker CHUNKER           Chunker ID: legacy, overlap, recursive_paragraph,
                              semantic, document_structure (default: legacy)
  -h, --help                  Show this message
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task) TASK="$2"; shift 2 ;;
        --output_dir) OUTPUT_DIR="$2"; shift 2 ;;
        --chunk_length) CHUNK_LENGTH="$2"; shift 2 ;;
        --input_length) INPUT_LENGTH="$2"; shift 2 ;;
        --context_length) CONTEXT_LENGTH="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --num_workers) NUM_WORKERS="$2"; shift 2 ;;
        --chunker) CHUNKER="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

# Verify Ollama is reachable
if ! curl -s http://localhost:11434/v1/models >/dev/null 2>&1; then
    echo "ERROR: Ollama server not reachable at http://localhost:11434/v1" >&2
    echo "Start it with:  ollama serve" >&2
    exit 1
fi

# Verify the requested model is available
if ! ollama list | grep -q "^${MODEL}\b"; then
    echo "ERROR: Model '${MODEL}' not found in Ollama." >&2
    echo "Pull it with:  ollama pull ${MODEL}" >&2
    exit 1
fi

cd "${REPO_ROOT}"

echo "[run] Task: ${TASK}"
echo "[run] Model: ${MODEL}"
echo "[run] Chunker: ${CHUNKER}"
echo "[run] Output: ${OUTPUT_DIR}"
echo "[run] Ollama endpoint: http://localhost:11434/v1"

python main.py \
    --task "${TASK}" \
    --output_dir "${OUTPUT_DIR}" \
    --chunk_length "${CHUNK_LENGTH}" \
    --input_length "${INPUT_LENGTH}" \
    --context_length "${CONTEXT_LENGTH}" \
    --api_url http://localhost:11434/v1 \
    --api_key ollama \
    --model "${MODEL}" \
    --num_workers "${NUM_WORKERS}" \
    --chunker "${CHUNKER}"
