#!/usr/bin/env bash
#
# Run ExtAgents against a local Ollama server.
#
# This uses the paper's homogeneous local model: Llama-3.2-3B-Instruct
# (Ollama tag: llama3.2:3b) for both Seeking and Reasoning roles.
#
# Requirements:
#   - Ollama server running:  ollama serve
#   - Model pulled:           ollama pull llama3.2:3b
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
#
#   # First 1000 RAG examples (preserves original positional IDs)
#   head -n 1000 data/rag_1000k.jsonl > data/rag_first1000.jsonl
#   bash scripts/run_extagents_ollama.sh --data_path data/rag_first1000.jsonl \
#       --output_dir results_rag_test --chunker overlap

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Defaults matching the paper's local baseline
TASK="rag"
OUTPUT_DIR="results_rag_ollama"
CHUNK_LENGTH=8000
INPUT_LENGTH=128000
CONTEXT_LENGTH=32768
MODEL="llama3.2:3b"
NUM_WORKERS=1
CHUNKER="legacy"
DATA_PATH=""

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --task {rag|en}             Task to run (default: rag)
  --output_dir DIR            Base output directory (default: results_rag_ollama)
  --data_path FILE            JSONL input (default: task's full dataset)
  --chunk_length N            Chunk size in tokens (default: 8000)
  --input_length N            Total input length in tokens (default: 128000)
  --context_length N          Model context length (default: 32768)
  --model MODEL               Ollama model tag (default: llama3.2:3b)
  --num_workers N             Parallel workers (default: 1)
  --chunker CHUNKER           Chunker ID: legacy, overlap, recursive_paragraph,
                              semantic, document_structure, semantic_tree (default: legacy)
  Results: DIR/CHUNKER/DATASET/final_preds_CHUNKER.jsonl
           (final_preds.jsonl in the same directory is the resume/eval file)
  -h, --help                  Show this message
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task) TASK="$2"; shift 2 ;;
        --output_dir) OUTPUT_DIR="$2"; shift 2 ;;
        --data_path) DATA_PATH="$2"; shift 2 ;;
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

cd "${REPO_ROOT}"

# Select input before contacting Ollama, so bad paths and options fail quickly.
case "${TASK}" in
    rag) DEFAULT_DATA_PATH="./data/rag_1000k.jsonl" ;;
    en)  DEFAULT_DATA_PATH="./data/longbook_qa_eng.jsonl" ;;
    *) echo "ERROR: Unsupported task: ${TASK} (expected rag or en)" >&2; exit 1 ;;
esac
case "${CHUNKER}" in
    legacy|overlap|recursive_paragraph|semantic|document_structure|semantic_tree) ;;
    *) echo "ERROR: Unknown chunker: ${CHUNKER}" >&2; exit 1 ;;
esac
DATA_PATH="${DATA_PATH:-${DEFAULT_DATA_PATH}}"
if [[ ! -f "${DATA_PATH}" ]]; then
    echo "ERROR: Data file not found: ${DATA_PATH}" >&2
    echo "Download it with:  bash scripts/download_data.sh" >&2
    exit 1
fi
DATASET="${DATA_PATH##*/}"
DATASET="${DATASET%.jsonl}"
RUN_DIR="${OUTPUT_DIR}/${CHUNKER}/${DATASET}"

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

echo "[run] Task: ${TASK}"
echo "[run] Model: ${MODEL}"
echo "[run] Chunker: ${CHUNKER}"
echo "[run] Output: ${RUN_DIR}"
echo "[run] Data: ${DATA_PATH}"
echo "[run] Ollama endpoint: http://localhost:11434/v1"

python "${REPO_ROOT}/main.py" \
    --task "${TASK}" \
    --output_dir "${RUN_DIR}" \
    --data_path "${DATA_PATH}" \
    --chunk_length "${CHUNK_LENGTH}" \
    --input_length "${INPUT_LENGTH}" \
    --context_length "${CONTEXT_LENGTH}" \
    --api_url http://localhost:11434/v1 \
    --api_key ollama \
    --model "${MODEL}" \
    --num_workers "${NUM_WORKERS}" \
    --chunker "${CHUNKER}"

cp "${RUN_DIR}/final_preds.jsonl" "${RUN_DIR}/final_preds_${CHUNKER}_${DATASET}.jsonl"
echo "[run] Named predictions: ${RUN_DIR}/final_preds_${CHUNKER}_${DATASET}.jsonl"
