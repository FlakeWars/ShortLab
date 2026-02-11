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

BREW_BIN=""

if [[ -x "/opt/homebrew/bin/brew" ]]; then
  BREW_BIN="/opt/homebrew/bin/brew"
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif command -v brew >/dev/null 2>&1; then
  BREW_BIN="$(command -v brew)"
fi

if [[ -z "${BREW_BIN}" ]]; then
  log "Homebrew not found. Installing..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [[ -x "/opt/homebrew/bin/brew" ]]; then
    BREW_BIN="/opt/homebrew/bin/brew"
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif command -v brew >/dev/null 2>&1; then
    BREW_BIN="$(command -v brew)"
  fi
fi

if [[ -z "${BREW_BIN}" ]]; then
  log "ERROR: Homebrew not available after install."
  exit 1
fi

if [[ -f "${ROOT_DIR}/Brewfile" ]]; then
  log "Installing brew dependencies from Brewfile (missing only)..."
  brews=()
  casks=()
  while read -r line; do
    case "${line}" in
      brew\ \"*\") brews+=("${line#brew \"}");;
      cask\ \"*\") casks+=("${line#cask \"}");;
    esac
  done < <(awk '/^(brew|cask) /{print}' "${ROOT_DIR}/Brewfile")

  for i in "${!brews[@]}"; do
    brews[$i]="${brews[$i]%\"}"
  done
  for i in "${!casks[@]}"; do
    casks[$i]="${casks[$i]%\"}"
  done

  for formula in "${brews[@]}"; do
    if "${BREW_BIN}" list --formula "${formula}" >/dev/null 2>&1; then
      log "brew ${formula}: already installed"
    else
      log "brew ${formula}: installing"
      "${BREW_BIN}" install "${formula}"
    fi
  done

  for cask in "${casks[@]}"; do
    if "${BREW_BIN}" list --cask "${cask}" >/dev/null 2>&1; then
      log "cask ${cask}: already installed"
      continue
    fi
    if [[ "${cask}" == "docker" ]]; then
      log "cask ${cask}: skipped (install manually)"
      continue
    fi
    if [[ "${cask}" == "docker" && -d "/Applications/Docker.app" ]]; then
      log "cask ${cask}: detected /Applications/Docker.app, skipping"
      continue
    fi
    log "cask ${cask}: installing"
    "${BREW_BIN}" install --cask "${cask}"
  done
else
  log "ERROR: Brewfile not found in repo root."
  exit 1
fi

MISE_BIN=""
if [[ -x "/opt/homebrew/bin/mise" ]]; then
  MISE_BIN="/opt/homebrew/bin/mise"
elif command -v mise >/dev/null 2>&1; then
  MISE_BIN="$(command -v mise)"
fi

if [[ -n "${MISE_BIN}" ]]; then
  log "Installing runtime versions via mise..."
  (cd "${ROOT_DIR}" && "${MISE_BIN}" install)
else
  log "WARNING: mise not found. Install via Brewfile or manually."
fi

if [[ -x "${ROOT_DIR}/scripts/install-godot.sh" ]]; then
  log "Installing Godot (pinned version)..."
  "${ROOT_DIR}/scripts/install-godot.sh"
else
  log "WARNING: scripts/install-godot.sh not executable or missing."
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
