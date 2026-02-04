#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${ROOT_DIR}/${VENV_DIR}/bin/python"

if [ ! -x "${PYTHON_BIN}" ]; then
  echo "Missing python in ${VENV_DIR}. Run: make venv && make deps-py-uv"
  exit 1
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required for pipeline E2E tests."
  exit 1
fi

if command -v docker >/dev/null 2>&1; then
  make -C "${ROOT_DIR}" infra-up >/dev/null
fi

# This test requires canonical schema. We reset + migrate to avoid local drift.
make -C "${ROOT_DIR}" db-reset >/dev/null

PYTHONPATH="${ROOT_DIR}" "${PYTHON_BIN}" -m pytest -q tests/test_idea_compiler_pipeline_e2e.py
