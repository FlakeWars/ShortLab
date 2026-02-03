#!/usr/bin/env bash
set -euo pipefail

PID_FILE="${TMPDIR:-/tmp}/shortlab-dev.pids"

if [ ! -f "${PID_FILE}" ]; then
  echo "No PID file found: ${PID_FILE}"
  exit 1
fi

while read -r pid; do
  if [ -n "${pid}" ]; then
    kill "${pid}" >/dev/null 2>&1 || true
  fi
done <"${PID_FILE}"

rm -f "${PID_FILE}"
echo "Stopped dev processes."
