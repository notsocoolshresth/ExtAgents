#!/usr/bin/env bash
#
# Build llama.cpp with CUDA 11.4 in user space (no root required).
#
# Tested for: Tesla V100, driver 460.91.03, CUDA 11.2 driver runtime.
# Strategy: install the CUDA 11.4 *toolkit* via conda (user-space only) and
# compile llama.cpp against it. The existing driver (460) supports CUDA 11.4
# runtime, so the resulting binary can run on the V100s without touching the
# system driver.
#
# Requirements:
#   - conda or miniconda installed in user space.
#   - git, cmake, make, g++ available (can also come from conda).
#   - ~15 GB free disk space.
#
# Usage:
#   bash scripts/setup_llama_cpp_cuda114.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_NAME="${ENV_NAME:-extagents-llama}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-${REPO_ROOT}/.llama_cpp}"
CUDA_VERSION="11.4"

log() { echo "[setup] $*"; }

# --------------------------------------------------------------------------- #
# 1. Verify conda is available
# --------------------------------------------------------------------------- #
if ! command -v conda &>/dev/null; then
    echo "ERROR: conda not found in PATH." >&2
    echo "Install Miniconda in user space with:" >&2
    echo "  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" >&2
    echo "  bash Miniconda3-latest-Linux-x86_64.sh -b -p \$HOME/miniconda3" >&2
    echo "  \$HOME/miniconda3/bin/conda init bash && source ~/.bashrc" >&2
    exit 1
fi

# --------------------------------------------------------------------------- #
# 2. Create conda environment with CUDA 11.4 toolkit
# --------------------------------------------------------------------------- #
log "Creating conda environment '${ENV_NAME}' (python=3.10, cudatoolkit=11.4)..."
conda create -y -n "${ENV_NAME}" python=3.10

# shellcheck source=/dev/null
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${ENV_NAME}"

log "Installing CUDA ${CUDA_VERSION} toolkit and build tools into the env..."
conda install -y -c conda-forge \
    cudatoolkit=11.4 \
    cudnn=8 \
    cmake \
    make \
    gxx_linux-64=10

# Make nvcc discoverable in this shell and record it for later activation
export CUDA_HOME="${CONDA_PREFIX}"
export PATH="${CUDA_HOME}/bin:${PATH}"
export CPATH="${CUDA_HOME}/include:${CPATH:-}"
export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"
export CC="${CONDA_PREFIX}/bin/gcc"
export CXX="${CONDA_PREFIX}/bin/g++"

if ! command -v nvcc &>/dev/null; then
    echo "ERROR: nvcc still not found after conda install." >&2
    exit 1
fi

log "nvcc version: $(nvcc --version | grep release)"

# --------------------------------------------------------------------------- #
# 3. Clone / update llama.cpp
# --------------------------------------------------------------------------- #
if [[ -d "${LLAMA_CPP_DIR}/.git" ]]; then
    log "Updating existing llama.cpp at ${LLAMA_CPP_DIR}..."
    git -C "${LLAMA_CPP_DIR}" pull --ff-only
else
    log "Cloning llama.cpp into ${LLAMA_CPP_DIR}..."
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "${LLAMA_CPP_DIR}"
fi

# --------------------------------------------------------------------------- #
# 4. Build llama.cpp with CUDA
# --------------------------------------------------------------------------- #
log "Building llama.cpp with CUDA ${CUDA_VERSION} support..."
rm -rf "${LLAMA_CPP_DIR}/build"
cmake -S "${LLAMA_CPP_DIR}" -B "${LLAMA_CPP_DIR}/build" \
    -DLLAMA_CUDA=ON \
    -DLLAMA_CUDA_FORCE_MMQ=OFF \
    -DCMAKE_CUDA_ARCHITECTURES="70" \
    -DCMAKE_BUILD_TYPE=Release

cmake --build "${LLAMA_CPP_DIR}/build" --config Release -j"$(nproc)"

# --------------------------------------------------------------------------- #
# 5. Write activation helper
# --------------------------------------------------------------------------- #
ACTIVATE_FILE="${REPO_ROOT}/activate_llama_cpp_cuda114.sh"
cat > "${ACTIVATE_FILE}" <<EOF
#!/usr/bin/env bash
# Source this file before running llama.cpp server:
#   source ./activate_llama_cpp_cuda114.sh

conda activate ${ENV_NAME}
export CUDA_HOME="\${CONDA_PREFIX}"
export PATH="\${CUDA_HOME}/bin:\${PATH}"
export CPATH="\${CUDA_HOME}/include:\${CPATH:-}"
export LD_LIBRARY_PATH="\${CUDA_HOME}/lib64:\${LD_LIBRARY_PATH:-}"
export LLAMA_CPP_DIR="${LLAMA_CPP_DIR}"
EOF
chmod +x "${ACTIVATE_FILE}"

# --------------------------------------------------------------------------- #
# 6. Report
# --------------------------------------------------------------------------- #
log "Build complete."
echo ""
echo "  llama.cpp dir : ${LLAMA_CPP_DIR}"
echo "  server binary : ${LLAMA_CPP_DIR}/build/bin/llama-server"
echo "  activation    : source ${ACTIVATE_FILE}"
echo ""
echo "Next steps:"
echo "  1. source ${ACTIVATE_FILE}"
echo "  2. python scripts/download_gguf_models.py --models all"
echo "  3. bash scripts/run_llama_cpp_server.sh --model reasoner"
echo ""
echo "NOTE: This uses the user-space CUDA 11.4 toolkit. It does NOT change the"
echo "system driver. The V100 (compute capability 7.0) is fully supported."
