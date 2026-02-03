#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${TMPDIR:-/tmp}/shortlab-dev.pids"

API_PORT="${API_PORT:-8016}"
UI_PORT="${UI_PORT:-5173}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/1}"
VENV_DIR="${VENV_DIR:-.venv}"
OPERATOR_TOKEN="${OPERATOR_TOKEN:-sekret}"

API_LOG="${TMPDIR:-/tmp}/shortlab-api.log"
UI_LOG="${TMPDIR:-/tmp}/shortlab-ui.log"
WORKER_LOG="${TMPDIR:-/tmp}/shortlab-worker.log"

if [ ! -d "${ROOT_DIR}/${VENV_DIR}" ]; then
  echo "Missing venv: ${VENV_DIR}. Create it first."
  exit 1
fi

if [ -f "${PID_FILE}" ]; then
  echo "PID file already exists: ${PID_FILE}"
  echo "Run scripts/stop-dev.sh first."
  exit 1
fi

cd "${ROOT_DIR}"

: >"${API_LOG}"
: >"${UI_LOG}"
: >"${WORKER_LOG}"

if command -v lsof >/dev/null 2>&1; then
  if lsof -iTCP:"${API_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "API port ${API_PORT} already in use. Stop the process or set API_PORT."
    exit 1
  fi
  if lsof -iTCP:"${UI_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "UI port ${UI_PORT} already in use. Stop the process or set UI_PORT."
    exit 1
  fi
fi

nohup bash -c \
  "OPERATOR_TOKEN='${OPERATOR_TOKEN}' REDIS_URL='${REDIS_URL}' VENV_DIR='${VENV_DIR}' API_PORT='${API_PORT}' make api" \
  >"${API_LOG}" 2>&1 &
API_PID=$!

nohup bash -c \
  "VITE_API_URL='http://localhost:${API_PORT}' VITE_API_TARGET='http://localhost:${API_PORT}' UI_PORT='${UI_PORT}' make ui" \
  >"${UI_LOG}" 2>&1 &
UI_PID=$!

nohup bash -c \
  "REDIS_URL='${REDIS_URL}' VENV_DIR='${VENV_DIR}' make worker" \
  >"${WORKER_LOG}" 2>&1 &
WORKER_PID=$!

printf "%s\n%s\n%s\n" "${API_PID}" "${UI_PID}" "${WORKER_PID}" >"${PID_FILE}"

echo "Started API:${API_PORT} UI:${UI_PORT} worker (REDIS=${REDIS_URL})"
echo "Logs: ${API_LOG}, ${UI_LOG}, ${WORKER_LOG}"
