#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSIONS_FILE="${ROOT_DIR}/versions.env"

log() { printf "[setup] %s\n" "$*"; }

if ! command -v xcode-select >/dev/null 2>&1; then
  log "ERROR: xcode-select not found. Install Xcode Command Line Tools first."
  exit 1
fi

if ! xcode-select -p >/dev/null 2>&1; then
  log "Xcode Command Line Tools not installed. Run: xcode-select --install"
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  log "Homebrew not found. Installing..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [[ -f "/opt/homebrew/bin/brew" ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
fi

if [[ -f "${ROOT_DIR}/Brewfile" ]]; then
  log "Installing brew dependencies from Brewfile..."
  brew bundle --file "${ROOT_DIR}/Brewfile"
else
  log "ERROR: Brewfile not found in repo root."
  exit 1
fi

if [[ -f "${VERSIONS_FILE}" ]]; then
  log "Pinned versions:"
  # shellcheck disable=SC1090
  source "${VERSIONS_FILE}"
  log "  Python: ${PYTHON_VERSION:-unset}"
  log "  Node: ${NODE_VERSION_LTS:-unset}"
  log "  FFmpeg: ${FFMPEG_VERSION:-unset}"
else
  log "WARNING: versions file not found: ${VERSIONS_FILE}"
fi

log "Verifying tool versions..."
python3 --version || true
node --version || true
ffmpeg -version | head -n 1 || true

log "Done. Next steps:"
log "- Create and activate Python venv"
log "- Install Python deps via uv/poetry"
log "- Start Docker Desktop, then docker compose up for infra"
