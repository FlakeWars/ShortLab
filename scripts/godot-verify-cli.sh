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
LOG_DIR="${OUT_DIR}/logs"

if [[ -z "${SCRIPT_PATH}" ]]; then
  echo "[godot-verify-cli] usage: $0 /path/to/script.gd" >&2
  exit 2
fi

if [[ "${SCRIPT_PATH}" != res://* ]]; then
  SCRIPT_PATH="$(python3 - "${SCRIPT_PATH}" <<'PY'
import os
import sys

path = sys.argv[1]
print(os.path.realpath(path))
PY
)"
fi

mkdir -p "${OUT_DIR}"
mkdir -p "${LOG_DIR}"

echo "[godot-verify-cli] validate (headless)"
GODOT_SCRIPT_PATH="${SCRIPT_PATH}" GODOT_SECONDS="${SECONDS}" GODOT_MAX_NODES="${MAX_NODES}" \
  "${GODOT_BIN}" --headless --log-file "${LOG_DIR}/validate.log" --path "${PROJECT_DIR}" --script "res://runner.gd"

echo "[godot-verify-cli] preview (write-movie)"
GODOT_SCRIPT_PATH="${SCRIPT_PATH}" GODOT_SECONDS="${SECONDS}" GODOT_MAX_NODES="${MAX_NODES}" \
  "${GODOT_BIN}" --log-file "${LOG_DIR}/preview.log" --path "${PROJECT_DIR}" --script "res://runner.gd" \
  --write-movie "${OUT_DIR}/preview.ogv" --fixed-fps "${FPS}"

echo "[godot-verify-cli] render (write-movie)"
GODOT_SCRIPT_PATH="${SCRIPT_PATH}" GODOT_SECONDS="${SECONDS}" GODOT_MAX_NODES="${MAX_NODES}" \
  "${GODOT_BIN}" --log-file "${LOG_DIR}/final.log" --path "${PROJECT_DIR}" --script "res://runner.gd" \
  --write-movie "${OUT_DIR}/final.ogv" --fixed-fps "${FPS}"
