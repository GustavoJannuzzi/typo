#!/usr/bin/env bash
# Sobe a interface local em http://127.0.0.1:7860
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d ".venv/Scripts" ]; then
  PY=".venv/Scripts/python.exe"        # Windows (Git Bash)
elif [ -d ".venv/bin" ]; then
  PY=".venv/bin/python"                # macOS / Linux
else
  echo "venv nao encontrado. Rode:"
  echo "  python -m venv .venv && .venv/bin/pip install -e ."
  exit 1
fi

exec "$PY" -m app.ui "$@"
