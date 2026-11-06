#!/usr/bin/env bash
# Starts Taxon with only Python: http://localhost:8000
set -e
cd "$(dirname "$0")/backend"
PY=python3; command -v python3 >/dev/null || PY=python
[ -d .venv ] || "$PY" -m venv .venv
source .venv/bin/activate
python -m pip install -q -r requirements.txt
echo "Taxon is starting at http://localhost:8000  (Ctrl+C to stop)"
( sleep 4; { command -v xdg-open >/dev/null && xdg-open http://localhost:8000; } || { command -v open >/dev/null && open http://localhost:8000; } || true ) >/dev/null 2>&1 &
python -m uvicorn app.main:app --port 8000
