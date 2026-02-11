#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSIONS_FILE="${ROOT_DIR}/versions.env"
INSTALL_DIR="${ROOT_DIR}/.tools/godot"
TMP_DIR="${ROOT_DIR}/.tools/tmp"

log() { printf "[godot-install] %s\n" "$*"; }

if [[ ! -f "${VERSIONS_FILE}" ]]; then
  log "ERROR: versions file not found: ${VERSIONS_FILE}"
  exit 1
fi

# shellcheck disable=SC1090
source "${VERSIONS_FILE}"

if [[ -z "${GODOT_VERSION:-}" ]]; then
  log "ERROR: GODOT_VERSION is not set in versions.env"
  exit 1
fi

VERSION="${GODOT_VERSION}"
BASE_URL="https://downloads.godotengine.org"
ARCHIVE_URL="${BASE_URL}/?flavor=stable&platform=macos.universal&slug=macos.universal.zip&version=${VERSION}"

mkdir -p "${INSTALL_DIR}" "${TMP_DIR}"

ARCHIVE_PATH="${TMP_DIR}/godot-${VERSION}-macos.zip"
TARGET_DIR="${INSTALL_DIR}/${VERSION}"

if [[ -d "${TARGET_DIR}/Godot.app" ]]; then
  log "Godot ${VERSION} already installed at ${TARGET_DIR}"
else
  log "Downloading Godot ${VERSION}..."
  curl -fsSL -o "${ARCHIVE_PATH}" "${ARCHIVE_URL}"
  log "Extracting..."
  rm -rf "${TARGET_DIR}"
  mkdir -p "${TARGET_DIR}"
  /usr/bin/unzip -q "${ARCHIVE_PATH}" -d "${TARGET_DIR}"
fi

if [[ ! -d "${TARGET_DIR}/Godot.app" ]]; then
  log "ERROR: Godot.app not found in ${TARGET_DIR}"
  exit 1
fi

ln -sfn "${TARGET_DIR}" "${INSTALL_DIR}/current"
log "Installed Godot ${VERSION} -> ${INSTALL_DIR}/current/Godot.app"
log "Binary: ${INSTALL_DIR}/current/Godot.app/Contents/MacOS/Godot"
