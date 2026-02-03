#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-.venv}"

if [[ ! -x "/usr/bin/xcrun" ]]; then
  echo "xcrun not found. Install Xcode Command Line Tools first."
  exit 1
fi

if [[ ! -d "${ROOT_DIR}/${VENV_DIR}" ]]; then
  echo "Missing venv: ${VENV_DIR}. Run: make venv"
  exit 1
fi

export SDKROOT="$(xcrun --sdk macosx --show-sdk-path)"
export PKG_CONFIG_PATH="/opt/homebrew/opt/cairo/lib/pkgconfig"
export CPPFLAGS="-I/opt/homebrew/opt/cairo/include"
export LDFLAGS="-arch arm64 -L/opt/homebrew/opt/cairo/lib"
export CFLAGS="-arch arm64"
export CC="/usr/bin/clang"
export CXX="/usr/bin/clang++"

if ! command -v meson >/dev/null 2>&1; then
  echo "Missing meson. Install via: brew install meson"
  exit 1
fi

"${ROOT_DIR}/${VENV_DIR}/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
"${ROOT_DIR}/${VENV_DIR}/bin/python" -m pip install --no-cache-dir "meson-python>=0.14" >/dev/null

"${ROOT_DIR}/${VENV_DIR}/bin/python" -m pip uninstall -y pycairo >/dev/null 2>&1 || true
"${ROOT_DIR}/${VENV_DIR}/bin/python" -m pip install --no-cache-dir --no-binary=pycairo --no-build-isolation pycairo

echo "pycairo build completed"
