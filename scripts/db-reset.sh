#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL not set. Add it to .env or export it before running."
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  if command -v docker >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
    if ! ${DOCKER_COMPOSE_CMD} version >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1; then
      DOCKER_COMPOSE_CMD="docker-compose"
    fi
  fi
fi

echo "Resetting database schema (public) for: ${DATABASE_URL}"
if command -v psql >/dev/null 2>&1; then
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO public;
SQL
else
  if [[ -z "${DOCKER_COMPOSE_CMD:-}" ]]; then
    echo "psql not found and docker compose unavailable."
    exit 1
  fi
  POSTGRES_USER="${POSTGRES_USER:-postgres}"
  POSTGRES_DB="${POSTGRES_DB:-shortlab}"
  ${DOCKER_COMPOSE_CMD} exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 <<'SQL'
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO public;
SQL
fi

cd "${ROOT_DIR}"
make db-migrate
echo "DB reset complete."
