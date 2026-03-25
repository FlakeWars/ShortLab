#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

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

API_PORT="${E2E_API_PORT:-18000}"
API_URL="http://127.0.0.1:${API_PORT}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
OPERATOR_TOKEN="${OPERATOR_TOKEN:-sekret}"
DEV_MANUAL_FLOW="${DEV_MANUAL_FLOW:-1}"
FFMPEG_TIMEOUT_S="${FFMPEG_TIMEOUT_S:-600}"
RQ_JOB_TIMEOUT="${RQ_JOB_TIMEOUT:-600}"
RQ_RENDER_TIMEOUT="${RQ_RENDER_TIMEOUT:-900}"
E2E_FORCE_TEMPLATE_COMPILER="${E2E_FORCE_TEMPLATE_COMPILER:-1}"
if [ "${E2E_FORCE_TEMPLATE_COMPILER}" = "1" ]; then
  IDEA_DSL_COMPILER_ENABLED="0"
else
  IDEA_DSL_COMPILER_ENABLED="${IDEA_DSL_COMPILER_ENABLED:-0}"
fi
VENV_BIN="${VENV_DIR:-.venv}/bin"

API_LOG="${TMPDIR:-/tmp}/shortlab-e2e-api.log"
WORKER_LOG="${TMPDIR:-/tmp}/shortlab-e2e-worker.log"

cleanup() {
  if [ -n "${API_PID:-}" ] && kill -0 "${API_PID}" >/dev/null 2>&1; then
    kill "${API_PID}" >/dev/null 2>&1 || true
  fi
  if [ -n "${WORKER_PID:-}" ] && kill -0 "${WORKER_PID}" >/dev/null 2>&1; then
    kill "${WORKER_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

post_json() {
  local path="$1"
  local body="$2"
  curl -sS -X POST "${API_URL}${path}" \
    -H "x-operator-token: ${OPERATOR_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${body}"
}

post_json_with_status() {
  local path="$1"
  local body="$2"
  curl -sS -w '\nHTTP_STATUS:%{http_code}\n' -X POST "${API_URL}${path}" \
    -H "x-operator-token: ${OPERATOR_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${body}"
}

video_stream_bitrate() {
  local file="$1"
  ffprobe -v error -select_streams v:0 -show_entries stream=bit_rate -of default=nw=1:nk=1 "$file" | head -n1
}

video_duration_seconds() {
  local file="$1"
  ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$file" | head -n1
}

frame_sha256_at() {
  local file="$1"
  local at="$2"
  local tmp_png
  tmp_png="$(mktemp "${TMPDIR:-/tmp}/shortlab-e2e-frame-XXXXXX.png")"
  ffmpeg -v error -ss "${at}" -i "$file" -frames:v 1 -y "$tmp_png" >/dev/null 2>&1 || true
  if [ ! -f "$tmp_png" ]; then
    rm -f "$tmp_png"
    echo ""
    return
  fi
  shasum "$tmp_png" | awk '{print $1}'
  rm -f "$tmp_png"
}

assert_video_not_static() {
  local file="$1"
  local label="$2"
  local min_bitrate="${E2E_MIN_VIDEO_BITRATE_BPS:-16000}"
  local min_duration="${E2E_MIN_VIDEO_DURATION_S:-3}"
  local max_tail_freeze_window="${E2E_MAX_TAIL_FREEZE_WINDOW_S:-0.5}"

  local bitrate
  bitrate="$(video_stream_bitrate "$file")"
  if [ -z "${bitrate}" ]; then
    bitrate="0"
  fi

  local duration
  duration="$(video_duration_seconds "$file")"
  if [ -z "${duration}" ]; then
    duration="0"
  fi
  local duration_int
  duration_int="$(printf '%.0f' "${duration}")"
  if [ "${duration_int}" -lt "${min_duration}" ]; then
    echo "[e2e][fail] ${label} invalid duration: duration=${duration}s min=${min_duration}s"
    exit 1
  fi

  local mid_ts
  mid_ts="$(awk -v d="${duration}" 'BEGIN { printf "%.3f", d/2.0 }')"
  local end_ts
  end_ts="$(awk -v d="${duration}" -v w="${max_tail_freeze_window}" 'BEGIN { t=d-w; if (t<0) t=0; printf "%.3f", t }')"

  local start_hash
  local mid_hash
  local end_hash
  start_hash="$(frame_sha256_at "$file" "0.000")"
  mid_hash="$(frame_sha256_at "$file" "${mid_ts}")"
  end_hash="$(frame_sha256_at "$file" "${end_ts}")"
  if [ -z "${start_hash}" ] || [ -z "${mid_hash}" ] || [ -z "${end_hash}" ]; then
    echo "[e2e][fail] ${label} cannot compute frame hashes"
    exit 1
  fi
  if [ "${start_hash}" = "${mid_hash}" ] && [ "${mid_hash}" = "${end_hash}" ]; then
    echo "[e2e][fail] ${label} static frames detected (start==mid==end)"
    exit 1
  fi
  if [ "${mid_hash}" = "${end_hash}" ]; then
    echo "[e2e][fail] ${label} frozen tail detected (mid==end)"
    exit 1
  fi
  if [ "${bitrate}" -lt "${min_bitrate}" ]; then
    echo "[e2e][fail] ${label} low bitrate: bitrate=${bitrate}bps min=${min_bitrate}bps"
    exit 1
  fi
}

echo "[e2e] Starting API on ${API_URL}"
PYTHONPATH="${ROOT_DIR}" REDIS_URL="${REDIS_URL}" DEV_MANUAL_FLOW="${DEV_MANUAL_FLOW}" OPERATOR_TOKEN="${OPERATOR_TOKEN}" \
  FFMPEG_TIMEOUT_S="${FFMPEG_TIMEOUT_S}" \
  RQ_JOB_TIMEOUT="${RQ_JOB_TIMEOUT}" RQ_RENDER_TIMEOUT="${RQ_RENDER_TIMEOUT}" \
  IDEA_DSL_COMPILER_ENABLED="${IDEA_DSL_COMPILER_ENABLED}" \
  "${ROOT_DIR}/${VENV_BIN}/uvicorn" api.main:app --host 127.0.0.1 --port "${API_PORT}" >"${API_LOG}" 2>&1 &
API_PID=$!

echo "[e2e] Starting worker (REDIS=${REDIS_URL})"
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES RQ_SIMPLE_WORKER=1 PYTHONPATH="${ROOT_DIR}" REDIS_URL="${REDIS_URL}" \
  RQ_JOB_TIMEOUT="${RQ_JOB_TIMEOUT}" RQ_RENDER_TIMEOUT="${RQ_RENDER_TIMEOUT}" \
  IDEA_DSL_COMPILER_ENABLED="${IDEA_DSL_COMPILER_ENABLED}" \
  "${ROOT_DIR}/${VENV_BIN}/python" "${ROOT_DIR}/scripts/worker.py" >"${WORKER_LOG}" 2>&1 &
WORKER_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "${API_URL}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS "${API_URL}/health" >/dev/null

E2E_IDEA_MODE="${E2E_IDEA_MODE:-text}"
E2E_STAMP="$(date +%s)"
E2E_TITLE="Niebieska kula zbiera czerwone punkty ${E2E_STAMP}"
E2E_SUMMARY="Jedna kula porusza sie po planszy i zbiera punkty, a tempo narasta (${E2E_STAMP})."
E2E_EXPECT="Widac zasade zbierania punktow i zmiane predkosci."
E2E_PREVIEW="Krotka, dynamiczna animacja z czytelna zasada."
echo "[e2e] Step 1/14: generate 1 PL idea candidate (mode=${E2E_IDEA_MODE})"
if [ "${E2E_IDEA_MODE}" = "llm" ]; then
  GEN="$(post_json "/idea-candidates/generate" '{"mode":"llm","limit":1,"language":"pl"}')"
else
  GEN="$(post_json "/idea-candidates/generate" "{\"mode\":\"text\",\"language\":\"pl\",\"title\":\"${E2E_TITLE}\",\"summary\":\"${E2E_SUMMARY}\",\"what_to_expect\":\"${E2E_EXPECT}\",\"preview\":\"${E2E_PREVIEW}\"}")"
fi

echo "[e2e] Step 2/14: sample candidate"
SAMPLE="$(curl -sS "${API_URL}/idea-repo/sample?limit=1")"
CID="$(printf '%s' "${SAMPLE}" | jq -r '.[0].id // empty')"
if [ -z "${CID}" ]; then
  if [ "${E2E_IDEA_MODE}" = "llm" ]; then
    echo "[e2e] fallback: llm returned no candidate, retrying with deterministic text mode"
    GEN="$(post_json "/idea-candidates/generate" "{\"mode\":\"text\",\"language\":\"pl\",\"title\":\"${E2E_TITLE}\",\"summary\":\"${E2E_SUMMARY}\",\"what_to_expect\":\"${E2E_EXPECT}\",\"preview\":\"${E2E_PREVIEW}\"}")"
    SAMPLE="$(curl -sS "${API_URL}/idea-repo/sample?limit=1")"
    CID="$(printf '%s' "${SAMPLE}" | jq -r '.[0].id // empty')"
  fi
fi
if [ -z "${CID}" ]; then
  echo "[e2e][fail] no candidate returned by /idea-repo/sample"
  echo "${GEN}" | jq .
  echo "${SAMPLE}" | jq .
  exit 1
fi

echo "[e2e] Step 3/14: pick candidate"
DECIDE="$(post_json "/idea-repo/decide" "{\"decisions\":[{\"idea_candidate_id\":\"${CID}\",\"decision\":\"picked\"}]}")"
IDEA_ID="$(printf '%s' "${DECIDE}" | jq -r '.idea_id // empty')"
if [ -z "${IDEA_ID}" ]; then
  echo "[e2e][fail] no idea_id after pick"
  echo "${DECIDE}" | jq .
  exit 1
fi

echo "[e2e] Step 4/14: compile gdscript"
COMPILE="$(post_json "/ops/godot/compile-gdscript" "{\"idea_id\":\"${IDEA_ID}\",\"validate\":true}")"
SCRIPT="$(printf '%s' "${COMPILE}" | jq -r '.script_path // empty')"
if [ -z "${SCRIPT}" ]; then
  echo "[e2e][fail] compile did not return script_path"
  echo "${COMPILE}" | jq .
  exit 1
fi

echo "[e2e] Step 5/14: validate script"
post_json "/ops/godot/validate" "{\"script_path\":\"${SCRIPT}\",\"seconds\":5,\"fps\":12,\"max_nodes\":200}" >/dev/null

echo "[e2e] Step 6/14: estimate duration"
post_json "/ops/godot/estimate-duration" "{\"script_path\":\"${SCRIPT}\",\"target_duration_s\":60,\"scout_seconds\":60,\"fps\":12}" >/dev/null

echo "[e2e] Step 7/14: preview"
PREVIEW="$(post_json "/ops/godot/preview" "{\"script_path\":\"${SCRIPT}\",\"seconds\":8,\"fps\":12,\"scale\":0.5}")"
PREVIEW_OUT="$(printf '%s' "${PREVIEW}" | jq -r '.out_path // empty')"

echo "[e2e] Step 8/14: intent-check"
INTENT="$(post_json "/ops/godot/intent-check" "{\"script_path\":\"${SCRIPT}\",\"scout_seconds\":60}")"
REC_SIM="$(printf '%s' "${INTENT}" | jq -r '.recommended_sim_duration_s // 60')"

echo "[e2e] Step 9/14: final render"
RENDER="$(post_json "/ops/godot/render" "{\"script_path\":\"${SCRIPT}\",\"seconds\":${REC_SIM},\"fps\":30}")"
FINAL_OUT="$(printf '%s' "${RENDER}" | jq -r '.out_path // empty')"
if [ -z "${FINAL_OUT}" ]; then
  echo "[e2e][fail] render did not return out_path"
  echo "${RENDER}" | jq .
  exit 1
fi
assert_video_not_static "${FINAL_OUT}" "final render"

echo "[e2e] Step 10/14: intro overlay (EN captions)"
INTRO="$(post_json_with_status "/ops/overlay/intro" "{\"input_path\":\"${FINAL_OUT}\",\"idea_id\":\"${IDEA_ID}\",\"language\":\"en\",\"duration_s\":1.5}")"
INTRO_STATUS="$(printf '%s' "${INTRO}" | awk -F: '/HTTP_STATUS/{print $2}' | tail -n1)"
INTRO_BODY="$(printf '%s' "${INTRO}" | sed '/HTTP_STATUS:/d')"
if [ "${INTRO_STATUS}" != "200" ]; then
  echo "[e2e][fail] intro overlay failed"
  if echo "${INTRO_BODY}" | jq . >/dev/null 2>&1; then
    echo "${INTRO_BODY}" | jq .
  else
    echo "${INTRO_BODY}"
  fi
  exit 1
fi
INTRO_OUT="$(printf '%s' "${INTRO_BODY}" | jq -r '.out_path // empty')"

echo "[e2e] Step 11/14: audio mix"
AUDIO="$(post_json_with_status "/ops/audio/mix" "{\"input_path\":\"${INTRO_OUT}\",\"keep_source_audio\":true,\"audio_profile\":\"balanced\"}")"
AUDIO_STATUS="$(printf '%s' "${AUDIO}" | awk -F: '/HTTP_STATUS/{print $2}' | tail -n1)"
AUDIO_BODY="$(printf '%s' "${AUDIO}" | sed '/HTTP_STATUS:/d')"
if [ "${AUDIO_STATUS}" != "200" ]; then
  echo "[e2e][fail] audio mix failed"
  if echo "${AUDIO_BODY}" | jq . >/dev/null 2>&1; then
    echo "${AUDIO_BODY}" | jq .
  else
    echo "${AUDIO_BODY}"
  fi
  exit 1
fi
assert_video_not_static "$(printf '%s' "${AUDIO_BODY}" | jq -r '.out_path // empty')" "final intro+audio render"

echo "[e2e] Step 12/14: enqueue pipeline for DB animation/render"
ENQUEUE="$(post_json "/ops/enqueue" "{\"dsl_template\":\".ai/examples/dsl-v1-happy.yaml\",\"out_root\":\"out/pipeline\",\"idea_gate\":false}")"
ANIMATION_ID="$(printf '%s' "${ENQUEUE}" | jq -r '.animation_id // empty')"
if [ -z "${ANIMATION_ID}" ]; then
  echo "[e2e][fail] enqueue did not return animation_id"
  echo "${ENQUEUE}" | jq .
  exit 1
fi

echo "[e2e] waiting for render row on animation=${ANIMATION_ID}"
RENDER_ID=""
for _ in $(seq 1 180); do
  JOBS="$(curl -sS "${API_URL}/pipeline/jobs?limit=200")"
  GEN_STATUS="$(printf '%s' "${JOBS}" | jq -r --arg aid "${ANIMATION_ID}" '[.[] | select(.job_type == "generate_dsl" and .payload.animation_id == $aid) | .status][0] // empty')"
  GEN_ERROR="$(printf '%s' "${JOBS}" | jq -r --arg aid "${ANIMATION_ID}" '[.[] | select(.job_type == "generate_dsl" and .payload.animation_id == $aid) | .error_payload.message][0] // empty')"
  RENDER_STATUS="$(printf '%s' "${JOBS}" | jq -r --arg aid "${ANIMATION_ID}" '[.[] | select(.job_type == "render" and .payload.animation_id == $aid) | .status][0] // empty')"
  RENDER_ERROR="$(printf '%s' "${JOBS}" | jq -r --arg aid "${ANIMATION_ID}" '[.[] | select(.job_type == "render" and .payload.animation_id == $aid) | .error_payload.message][0] // empty')"

  if [ "${GEN_STATUS}" = "failed" ]; then
    echo "[e2e][fail] generate_dsl job failed for animation=${ANIMATION_ID}"
    echo "[e2e][fail] ${GEN_ERROR}"
    exit 1
  fi
  if [ "${RENDER_STATUS}" = "failed" ]; then
    echo "[e2e][fail] render job failed for animation=${ANIMATION_ID}"
    echo "[e2e][fail] ${RENDER_ERROR}"
    exit 1
  fi

  ANIMATIONS="$(curl -sS "${API_URL}/animations?limit=200")"
  RENDER_ID="$(printf '%s' "${ANIMATIONS}" | jq -r --arg aid "${ANIMATION_ID}" '[.[] | select(.id == $aid) | .render.id][0] // empty')"
  if [ -n "${RENDER_ID}" ]; then
    break
  fi
  sleep 2
done
if [ -z "${RENDER_ID}" ]; then
  echo "[e2e][fail] missing render row for animation_id=${ANIMATION_ID}"
  echo "${ANIMATIONS}" | jq .
  exit 1
fi

echo "[e2e] Step 13/14: QC accepted + publish manual_confirmed"
QC_RAW="$(post_json_with_status "/ops/qc-decide" "{\"animation_id\":\"${ANIMATION_ID}\",\"result\":\"accepted\",\"notes\":\"e2e\",\"decision_payload\":{\"idea_intent_ok\":true,\"intro_readability_ok\":true,\"audio_quality_ok\":true}}")"
QC_STATUS="$(printf '%s' "${QC_RAW}" | awk -F: '/HTTP_STATUS/{print $2}' | tail -n1)"
QC="$(printf '%s' "${QC_RAW}" | sed '/HTTP_STATUS:/d')"
if [ "${QC_STATUS}" != "200" ]; then
  echo "[e2e][fail] qc-decide failed"
  echo "${QC}" | jq .
  exit 1
fi

PUBLISH_RAW="$(post_json_with_status "/ops/publish-record" "{\"render_id\":\"${RENDER_ID}\",\"platform\":\"youtube\",\"status\":\"manual_confirmed\",\"content_id\":\"e2e-${ANIMATION_ID}\"}")"
PUBLISH_STATUS="$(printf '%s' "${PUBLISH_RAW}" | awk -F: '/HTTP_STATUS/{print $2}' | tail -n1)"
PUBLISH="$(printf '%s' "${PUBLISH_RAW}" | sed '/HTTP_STATUS:/d')"
if [ "${PUBLISH_STATUS}" != "200" ]; then
  echo "[e2e][fail] publish-record failed"
  echo "${PUBLISH}" | jq .
  exit 1
fi
PUBLISH_ID="$(printf '%s' "${PUBLISH}" | jq -r '.publish_record_id // empty')"
if [ -z "${PUBLISH_ID}" ]; then
  echo "[e2e][fail] publish_record missing id"
  echo "${PUBLISH}" | jq .
  exit 1
fi

echo "[e2e] Step 14/14: metrics upsert + insights"
TODAY="$(date +%F)"
METRICS_RAW="$(post_json_with_status "/ops/metrics-daily" "{\"platform_type\":\"youtube\",\"content_id\":\"e2e-${ANIMATION_ID}\",\"date\":\"${TODAY}\",\"publish_record_id\":\"${PUBLISH_ID}\",\"render_id\":\"${RENDER_ID}\",\"views\":123,\"likes\":9,\"comments\":2,\"shares\":1,\"watch_time_seconds\":456}")"
METRICS_STATUS="$(printf '%s' "${METRICS_RAW}" | awk -F: '/HTTP_STATUS/{print $2}' | tail -n1)"
METRICS="$(printf '%s' "${METRICS_RAW}" | sed '/HTTP_STATUS:/d')"
if [ "${METRICS_STATUS}" != "200" ]; then
  echo "[e2e][fail] metrics upsert failed"
  echo "${METRICS}" | jq .
  exit 1
fi
INSIGHTS="$(curl -sS -H "x-operator-token: ${OPERATOR_TOKEN}" "${API_URL}/insights/summary")"

echo "[e2e][ok] full flow passed"
jq -n \
  --arg idea_id "${IDEA_ID}" \
  --arg candidate_id "${CID}" \
  --arg script_path "${SCRIPT}" \
  --arg preview_out "${PREVIEW_OUT}" \
  --arg final_out "${FINAL_OUT}" \
  --arg animation_id "${ANIMATION_ID}" \
  --arg render_id "${RENDER_ID}" \
  --arg publish_record_id "${PUBLISH_ID}" \
  --argjson qc "${QC}" \
  --argjson publish "${PUBLISH}" \
  --argjson metrics "${METRICS}" \
  --argjson insights "${INSIGHTS}" \
  '{
    candidate_id:$candidate_id,
    idea_id:$idea_id,
    script_path:$script_path,
    preview_out:$preview_out,
    final_out:$final_out,
    animation_id:$animation_id,
    render_id:$render_id,
    publish_record_id:$publish_record_id,
    qc: $qc,
    publish: $publish,
    metrics: $metrics,
    insights_recommendation: $insights.recommendation,
    insights_code: $insights.recommendation_code
  }'
