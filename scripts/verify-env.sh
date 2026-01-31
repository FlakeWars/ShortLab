#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSIONS_FILE="${ROOT_DIR}/versions.env"

if [[ -x "/opt/homebrew/bin/brew" ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

if [[ ! -f "${VERSIONS_FILE}" ]]; then
  echo "[verify] ERROR: versions file not found: ${VERSIONS_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${VERSIONS_FILE}"

fail=0

check_version() {
  local name="$1"
  local want_prefix="$2"
  local have="$3"

  if [[ -z "${want_prefix}" ]]; then
    echo "[verify] ${name}: skip (no pinned version)"
    return 0
  fi

  if [[ "${have}" == ${want_prefix}* ]]; then
    echo "[verify] ${name}: OK (${have})"
  else
    echo "[verify] ${name}: FAIL (want ${want_prefix}*, have ${have})"
    fail=1
  fi
}

get_cmd_version() {
  local cmd="$1"
  local fmt="$2"

  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "missing"
    return 0
  fi

  eval "${fmt}"
}

get_mise_version() {
  local cmd="$1"
  local fmt="$2"

  if command -v mise >/dev/null 2>&1 && [[ -f "${ROOT_DIR}/.mise.toml" ]]; then
    eval "mise exec -- ${fmt}" 2>/dev/null || echo "missing"
    return 0
  fi

  get_cmd_version "${cmd}" "${fmt}"
}

get_compose_tag() {
  local image_name="$1"
  local tag=""
  local file

  for file in "${ROOT_DIR}/docker-compose.yml" \
              "${ROOT_DIR}/docker-compose.yaml" \
              "${ROOT_DIR}/compose.yml" \
              "${ROOT_DIR}/compose.yaml"; do
    if [[ -f "${file}" ]]; then
      tag=$(awk -v img="${image_name}" '
        $0 ~ "image:" && $0 ~ img {
          gsub(/["'\'' ]/, "", $0);
          split($0, parts, ":");
          if (length(parts) >= 3) { print parts[3]; exit }
        }' "${file}")
      if [[ -n "${tag}" ]]; then
        echo "${tag}"
        return 0
      fi
    fi
  done

  return 1
}

python_v=$(get_mise_version "python3" "python3 --version | awk '{print \$2}'")
node_v=$(get_mise_version "node" "node --version | sed 's/^v//'")
ffmpeg_v=$(get_cmd_version "ffmpeg" "ffmpeg -version 2>/dev/null | head -n 1 | awk '{print \$3}'")
cairo_v=$(get_cmd_version "pkg-config" "pkg-config --modversion cairo 2>/dev/null")
skia_v=$(python3 - <<'PY' 2>/dev/null || true
import skia
print(skia.__version__)
PY
)
postgres_v=$(get_cmd_version "psql" "psql --version 2>/dev/null | awk '{print \$3}'")
redis_v=$(get_cmd_version "redis-server" "redis-server --version 2>/dev/null | sed -n 's/.*v=\\([0-9.]*\\).*/\\1/p'")
minio_v=$(get_cmd_version "minio" "minio --version 2>/dev/null | awk '{print \$3}'")

if [[ -z "${postgres_v}" ]]; then
  postgres_v=$(get_compose_tag "postgres")
fi
if [[ -z "${redis_v}" ]]; then
  redis_v=$(get_compose_tag "redis")
fi
if [[ -z "${minio_v}" ]]; then
  minio_v=$(get_compose_tag "minio/minio")
fi
if [[ -z "${minio_v}" ]]; then
  minio_v=$(get_compose_tag "minio")
fi

check_version "Python" "${PYTHON_VERSION}" "${python_v:-missing}"
check_version "Node" "${NODE_VERSION_LTS}" "${node_v:-missing}"
check_version "FFmpeg" "${FFMPEG_VERSION}" "${ffmpeg_v:-missing}"
check_version "Cairo" "${CAIRO_VERSION}" "${cairo_v:-missing}"

if [[ "${skia_v:-missing}" == "missing" ]]; then
  echo "[verify] skia-python: WARN (missing, optional at this stage)"
else
  check_version "skia-python" "${SKIA_PYTHON_VERSION}" "${skia_v:-missing}"
fi

if [[ "${postgres_v:-missing}" == "missing" ]]; then
  echo "[verify] Postgres: WARN (missing, expected via docker compose)"
else
  check_version "Postgres" "${POSTGRES_VERSION}" "${postgres_v:-missing}"
fi

if [[ "${redis_v:-missing}" == "missing" ]]; then
  echo "[verify] Redis: WARN (missing, expected via docker compose)"
else
  check_version "Redis" "${REDIS_VERSION}" "${redis_v:-missing}"
fi

if [[ "${minio_v:-missing}" == "missing" ]]; then
  echo "[verify] MinIO: WARN (missing, expected via docker compose)"
else
  check_version "MinIO" "${MINIO_VERSION}" "${minio_v:-missing}"
fi

if [[ $fail -ne 0 ]]; then
  echo "[verify] Environment verification failed"
  exit 1
fi

echo "[verify] Environment OK"
