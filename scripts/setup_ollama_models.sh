#!/usr/bin/env bash
#
# Pull the Ollama models matching the ExtAgents paper's local setup.
#
# Models pulled:
#   - llama3.1:8b  -> Reasoning Agent (and homogeneous Seeking + Reasoning)
#   - llama3.2:3b  -> Seeking Agent (heterogeneous / efficiency setup)
#
# Requirements:
#   - Ollama installed and running on GPU (verified by `ollama list`).
#   - The current ExtAgents code uses a single model endpoint, so the default
#     run uses llama3.1:8b for both roles. A future code change is needed to
#     route Seeking and Reasoning to different Ollama instances.

set -eo pipefail

log() { echo "[ollama-setup] $*"; }

if ! command -v ollama &>/dev/null; then
    echo "ERROR: ollama not found in PATH." >&2
    exit 1
fi

log "Pulling llama3.1:8b (paper's local model for both roles)..."
ollama pull llama3.1:8b

log "Pulling llama3.2:3b (paper's efficient Seeking Agent)..."
ollama pull llama3.2:3b

log "Done. Installed models:"
ollama list

log ""
log "Next steps:"
log "  1. Ensure ollama server is running:  ollama serve"
log "  2. Run ExtAgents with:  bash scripts/run_extagents_ollama.sh"
