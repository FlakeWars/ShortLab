#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${TMPDIR:-/tmp}/shortlab-dev.pids"

if [ -f "${ROOT_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "${ROOT_DIR}/.env"
  set +a
fi
if [ -f "${ROOT_DIR}/.env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  . "${ROOT_DIR}/.env.local"
  set +a
fi

API_PORT="${API_PORT:-8016}"
UI_PORT="${UI_PORT:-5173}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/1}"
VENV_DIR="${VENV_DIR:-.venv}"
OPERATOR_TOKEN="${OPERATOR_TOKEN:-sekret}"
RUN_DEV_HEALTHCHECK_RETRIES="${RUN_DEV_HEALTHCHECK_RETRIES:-30}"
RUN_DEV_HEALTHCHECK_INTERVAL_S="${RUN_DEV_HEALTHCHECK_INTERVAL_S:-1}"
RUN_DEV_HEALTHCHECK_URL="${RUN_DEV_HEALTHCHECK_URL:-http://localhost:${API_PORT}/health}"

API_LOG="${TMPDIR:-/tmp}/shortlab-api.log"
UI_LOG="${TMPDIR:-/tmp}/shortlab-ui.log"
WORKER_LOG="${TMPDIR:-/tmp}/shortlab-worker.log"

start_bg() {
  local cmd="$1"
  local log="$2"
  nohup bash -lc "${cmd}" >"${log}" 2>&1 &
}

wait_for_healthcheck() {
  if ! command -v curl >/dev/null 2>&1; then
    echo "Skipping healthcheck wait: curl not found."
    return 0
  fi
  local attempt=1
  while [ "${attempt}" -le "${RUN_DEV_HEALTHCHECK_RETRIES}" ]; do
    if curl -fsS --max-time 2 "${RUN_DEV_HEALTHCHECK_URL}" >/dev/null 2>&1; then
      echo "API healthcheck passed (${RUN_DEV_HEALTHCHECK_URL}) on attempt ${attempt}/${RUN_DEV_HEALTHCHECK_RETRIES}."
      return 0
    fi
    sleep "${RUN_DEV_HEALTHCHECK_INTERVAL_S}"
    attempt=$((attempt + 1))
  done
  echo "API healthcheck failed after ${RUN_DEV_HEALTHCHECK_RETRIES} retries: ${RUN_DEV_HEALTHCHECK_URL}"
  echo "See API log: ${API_LOG}"
  return 1
}

kill_port() {
  local port="$1"
  local pids
  if ! command -v lsof >/dev/null 2>&1; then
    return 0
  fi
  pids="$(lsof -ti tcp:"${port}" 2>/dev/null || true)"
  if [ -z "${pids}" ]; then
    return 0
  fi
  echo "Port ${port} is busy, stopping existing process(es): ${pids}"
  # shellcheck disable=SC2086
  kill ${pids} >/dev/null 2>&1 || true
  sleep 1
  pids="$(lsof -ti tcp:"${port}" 2>/dev/null || true)"
  if [ -n "${pids}" ]; then
    # shellcheck disable=SC2086
    kill -9 ${pids} >/dev/null 2>&1 || true
  fi
}

if [ ! -d "${ROOT_DIR}/${VENV_DIR}" ]; then
  echo "Missing venv: ${VENV_DIR}. Create it first."
  exit 1
fi

if [ -f "${PID_FILE}" ]; then
  alive=0
  while read -r line; do
    if [[ "${line}" == pid:* ]]; then
      pid="${line#pid:}"
    elif [[ "${line}" =~ ^[0-9]+$ ]]; then
      pid="${line}"
    else
      continue
    fi
    if [ -n "${pid}" ] && kill -0 "${pid}" >/dev/null 2>&1; then
      alive=1
      break
    fi
  done <"${PID_FILE}"
  if [ "${alive}" -eq 1 ]; then
    echo "run-dev already active (PID file: ${PID_FILE})."
    exit 0
  fi
  echo "Removing stale PID file: ${PID_FILE}"
  rm -f "${PID_FILE}"
fi

cd "${ROOT_DIR}"

: >"${API_LOG}"
: >"${UI_LOG}"
: >"${WORKER_LOG}"

kill_port "${API_PORT}"
kill_port "${UI_PORT}"

REDIS_URL="${REDIS_URL}" PYTHONPATH="${ROOT_DIR}" "${ROOT_DIR}/${VENV_DIR}/bin/python" \
  "${ROOT_DIR}/scripts/cleanup-rq-failed.py" --all >/dev/null 2>&1 || true
CLEANUP_OLDER_MIN="${CLEANUP_OLDER_MIN:-30}"
REDIS_URL="${REDIS_URL}" PYTHONPATH="${ROOT_DIR}" "${ROOT_DIR}/${VENV_DIR}/bin/python" \
  "${ROOT_DIR}/scripts/cleanup-jobs.py" --older-min "${CLEANUP_OLDER_MIN}" >/dev/null 2>&1 || true

start_bg "OPERATOR_TOKEN='${OPERATOR_TOKEN}' REDIS_URL='${REDIS_URL}' VENV_DIR='${VENV_DIR}' API_PORT='${API_PORT}' make api" "${API_LOG}"
API_PID=$!

start_bg "VITE_API_URL='http://localhost:${API_PORT}' VITE_API_TARGET='http://localhost:${API_PORT}' UI_PORT='${UI_PORT}' make ui" "${UI_LOG}"
UI_PID=$!

start_bg "REDIS_URL='${REDIS_URL}' VENV_DIR='${VENV_DIR}' make worker" "${WORKER_LOG}"
WORKER_PID=$!

printf "pid:%s\npid:%s\npid:%s\n" "${API_PID}" "${UI_PID}" "${WORKER_PID}" >"${PID_FILE}"

echo "Started API:${API_PORT} UI:${UI_PORT} worker (REDIS=${REDIS_URL})"
echo "Logs: ${API_LOG}, ${UI_LOG}, ${WORKER_LOG}"
wait_for_healthcheck
