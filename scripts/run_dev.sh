#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

(
  cd "$ROOT_DIR"
  uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
) &

(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --host 0.0.0.0 --port 5173
)
