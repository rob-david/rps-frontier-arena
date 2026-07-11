#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [ ! -d "frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

if [ "${FORCE_BUILD:-0}" = "1" ] || [ ! -d "frontend/out" ]; then
  echo "Building frontend static export..."
  (cd frontend && npm run build)
else
  echo "Using existing frontend/out (set FORCE_BUILD=1 to rebuild)."
fi

PORT="${PORT:-8000}"
echo "Starting FastAPI on port ${PORT}..."
uv run uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
