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

kill_children() {
  local parent_pid="$1"
  local child_pids=""
  if command -v pgrep >/dev/null 2>&1; then
    child_pids="$(pgrep -P "${parent_pid}" 2>/dev/null || true)"
  fi
  for child in ${child_pids}; do
    kill_children "${child}"
    kill "${child}" >/dev/null 2>&1 || true
    sleep 0.1
    kill -0 "${child}" >/dev/null 2>&1 && kill -9 "${child}" >/dev/null 2>&1 || true
  done
}

if [ -f "${PID_FILE}" ]; then
  while read -r line; do
    if [[ "${line}" == pid:* ]]; then
      pid="${line#pid:}"
    elif [[ "${line}" =~ ^[0-9]+$ ]]; then
      pid="${line}"
    else
      continue
    fi
    if [ -n "${pid}" ]; then
      kill_children "${pid}"
      kill "${pid}" >/dev/null 2>&1 || true
      sleep 0.2
      kill -0 "${pid}" >/dev/null 2>&1 && kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
  done <"${PID_FILE}"
  rm -f "${PID_FILE}"
fi

kill_port "${API_PORT}"
kill_port "${UI_PORT}"

echo "Stopped dev processes (if any)."
