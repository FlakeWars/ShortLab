#!/usr/bin/env bash
set -euo pipefail

FRONTEND_DIR="${1:-frontend}"
TEMPLATE="${2:-react-ts}"

if [ -d "$FRONTEND_DIR" ]; then
  echo "Frontend directory already exists: $FRONTEND_DIR"
  exit 1
fi

npm create vite@latest "$FRONTEND_DIR" -- --template "$TEMPLATE"
