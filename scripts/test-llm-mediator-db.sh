#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${ROOT_DIR}/${VENV_DIR}/bin/python"

if [ ! -x "${PYTHON_BIN}" ]; then
  echo "Missing python in ${VENV_DIR}. Run: make venv && make deps-py-uv"
  exit 1
fi

# Ensure infra is available for non-skipped DB integration tests.
if command -v docker >/dev/null 2>&1; then
  make -C "${ROOT_DIR}" infra-up >/dev/null
fi

PYTHONPATH="${ROOT_DIR}" "${PYTHON_BIN}" - <<'PY'
import os
import time
from sqlalchemy import text
from db.session import SessionLocal

deadline = time.time() + 30
last_err = None
while time.time() < deadline:
    try:
        with SessionLocal() as session:
            session.execute(text("select 1"))
        print("Postgres ready")
        raise SystemExit(0)
    except Exception as exc:
        last_err = exc
        time.sleep(1)

print(f"Postgres not ready after 30s: {last_err}")
raise SystemExit(1)
PY

PYTHONPATH="${ROOT_DIR}" "${PYTHON_BIN}" -m pytest -q \
  tests/test_llm_mediator.py \
  tests/test_llm_mediator_db_integration.py
