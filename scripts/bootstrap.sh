#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

python -m pip install -e "$ROOT_DIR[dev]"
cd "$ROOT_DIR/frontend"
npm install

