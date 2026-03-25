#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${ROOT_DIR}/${VENV_DIR}/bin/python"
SCRIPT_PATH="${1:-${ROOT_DIR}/renderer/godot/examples/bouncing_gap.gd}"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/out/manual-godot/smoke}"
SECONDS="${GODOT_SMOKE_SECONDS:-2}"
FPS="${GODOT_SMOKE_FPS:-12}"
MAX_NODES="${GODOT_SMOKE_MAX_NODES:-200}"
PREVIEW_SCALE="${GODOT_SMOKE_PREVIEW_SCALE:-0.5}"

if [ ! -x "${PYTHON_BIN}" ]; then
  echo "Missing python in ${VENV_DIR}. Run: make venv && make deps-py-uv"
  exit 1
fi

if [ ! -f "${SCRIPT_PATH}" ]; then
  echo "Missing script: ${SCRIPT_PATH}"
  exit 1
fi

mkdir -p "${OUT_DIR}"

run_step() {
  local mode="$1"
  local out_path="$2"
  local -a extra_args=()
  if [ "${mode}" = "preview" ]; then
    extra_args+=(--scale "${PREVIEW_SCALE}")
  fi
  if [ -n "${out_path}" ]; then
    extra_args+=(--out "${out_path}")
  fi

  local output
  if [ "${#extra_args[@]}" -gt 0 ]; then
    output="$(
      PYTHONPATH="${ROOT_DIR}" "${PYTHON_BIN}" "${ROOT_DIR}/scripts/godot-run.py" \
        --mode "${mode}" \
        --script "${SCRIPT_PATH}" \
        --seconds "${SECONDS}" \
        --fps "${FPS}" \
        --max-nodes "${MAX_NODES}" \
        "${extra_args[@]}" 2>&1
    )"
  else
    output="$(
      PYTHONPATH="${ROOT_DIR}" "${PYTHON_BIN}" "${ROOT_DIR}/scripts/godot-run.py" \
        --mode "${mode}" \
        --script "${SCRIPT_PATH}" \
        --seconds "${SECONDS}" \
        --fps "${FPS}" \
        --max-nodes "${MAX_NODES}" 2>&1
    )"
  fi
  echo "${output}" >"${OUT_DIR}/${mode}.log"
  if echo "${output}" | rg -q "Warning treated as error"; then
    echo "Godot parser warning treated as error detected in ${mode}.log"
    exit 1
  fi
}

echo "Running Godot smoke on: ${SCRIPT_PATH}"
run_step "validate" ""
run_step "preview" "${OUT_DIR}/preview.mp4"
run_step "render" "${OUT_DIR}/final.mp4"

if [ ! -f "${OUT_DIR}/preview.mp4" ]; then
  echo "Missing preview output: ${OUT_DIR}/preview.mp4"
  exit 1
fi
if [ ! -f "${OUT_DIR}/final.mp4" ]; then
  echo "Missing render output: ${OUT_DIR}/final.mp4"
  exit 1
fi

echo "Godot smoke OK: validate + preview + render"
echo "Artifacts: ${OUT_DIR}/preview.mp4, ${OUT_DIR}/final.mp4"
