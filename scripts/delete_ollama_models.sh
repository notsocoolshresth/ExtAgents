#!/usr/bin/env bash
#
# Remove the Ollama models used by ExtAgents.

set -eo pipefail

if ! command -v ollama &>/dev/null; then
    echo "ERROR: ollama not found in PATH." >&2
    exit 1
fi

MODELS=("llama3.1:8b" "llama3.2:3b")

for model in "${MODELS[@]}"; do
    if ollama list | grep -q "^${model}\b"; then
        echo "[delete] Removing ${model}..."
        ollama rm "${model}"
    else
        echo "[delete] ${model} not found, skipping."
    fi
done

echo "[delete] Done. Remaining models:"
ollama list
