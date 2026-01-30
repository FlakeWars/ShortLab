#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSIONS_FILE="${ROOT_DIR}/versions.env"

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

python_v=$(python3 --version 2>/dev/null | awk '{print $2}')
node_v=$(node --version 2>/dev/null | sed 's/^v//')
ffmpeg_v=$(ffmpeg -version 2>/dev/null | head -n 1 | awk '{print $3}')
cairo_v=$(pkg-config --modversion cairo 2>/dev/null || true)
skia_v=$(python3 - <<'PY' 2>/dev/null || true
import skia
print(skia.__version__)
PY
)
postgres_v=$(psql --version 2>/dev/null | awk '{print $3}')
redis_v=$(redis-server --version 2>/dev/null | sed -n 's/.*v=\\([0-9.]*\\).*/\\1/p')
minio_v=$(minio --version 2>/dev/null | awk '{print $3}')

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
check_version "skia-python" "${SKIA_PYTHON_VERSION}" "${skia_v:-missing}"
check_version "Postgres" "${POSTGRES_VERSION}" "${postgres_v:-missing}"
check_version "Redis" "${REDIS_VERSION}" "${redis_v:-missing}"
check_version "MinIO" "${MINIO_VERSION}" "${minio_v:-missing}"

if [[ $fail -ne 0 ]]; then
  echo "[verify] Environment verification failed"
  exit 1
fi

echo "[verify] Environment OK"
