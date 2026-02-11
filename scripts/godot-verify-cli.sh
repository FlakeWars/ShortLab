#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/renderer/godot"
GODOT_BIN="${GODOT_BIN:-godot}"
SCRIPT_PATH="${1:-}"
SECONDS="${GODOT_SECONDS:-2}"
FPS="${GODOT_FPS:-30}"
MAX_NODES="${GODOT_MAX_NODES:-200}"
OUT_DIR="${ROOT_DIR}/out/godot"

if [[ -z "${SCRIPT_PATH}" ]]; then
  echo "[godot-verify-cli] usage: $0 /path/to/script.gd" >&2
  exit 2
fi

mkdir -p "${OUT_DIR}"

echo "[godot-verify-cli] validate (headless)"
GODOT_SCRIPT_PATH="${SCRIPT_PATH}" GODOT_SECONDS="${SECONDS}" GODOT_MAX_NODES="${MAX_NODES}" \
  "${GODOT_BIN}" --headless --path "${PROJECT_DIR}" --script "res://runner.gd"

echo "[godot-verify-cli] preview (write-movie)"
GODOT_SCRIPT_PATH="${SCRIPT_PATH}" GODOT_SECONDS="${SECONDS}" GODOT_MAX_NODES="${MAX_NODES}" \
  "${GODOT_BIN}" --path "${PROJECT_DIR}" --script "res://runner.gd" \
  --write-movie "${OUT_DIR}/preview.mp4" --fixed-fps "${FPS}"

echo "[godot-verify-cli] render (write-movie)"
GODOT_SCRIPT_PATH="${SCRIPT_PATH}" GODOT_SECONDS="${SECONDS}" GODOT_MAX_NODES="${MAX_NODES}" \
  "${GODOT_BIN}" --path "${PROJECT_DIR}" --script "res://runner.gd" \
  --write-movie "${OUT_DIR}/final.mp4" --fixed-fps "${FPS}"
