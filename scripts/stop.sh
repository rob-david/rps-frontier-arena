#!/usr/bin/env bash
set -euo pipefail

if command -v pkill >/dev/null 2>&1; then
  pkill -f "uvicorn backend.main:app" || true
  echo "Requested stop for uvicorn backend.main:app"
else
  echo "pkill not available. Stop the uvicorn process manually."
fi
