#!/usr/bin/env bash
set -euo pipefail

PID_FILE="${TMPDIR:-/tmp}/shortlab-dev.pids"
API_PORT="${API_PORT:-8016}"
UI_PORT="${UI_PORT:-5173}"

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
  # shellcheck disable=SC2086
  kill ${pids} >/dev/null 2>&1 || true
  sleep 1
  pids="$(lsof -ti tcp:"${port}" 2>/dev/null || true)"
  if [ -n "${pids}" ]; then
    # shellcheck disable=SC2086
    kill -9 ${pids} >/dev/null 2>&1 || true
  fi
}

if [ -f "${PID_FILE}" ]; then
  while read -r pid; do
    if [ -n "${pid}" ]; then
      kill "${pid}" >/dev/null 2>&1 || true
    fi
  done <"${PID_FILE}"
  rm -f "${PID_FILE}"
fi

kill_port "${API_PORT}"
kill_port "${UI_PORT}"

echo "Stopped dev processes (if any)."
