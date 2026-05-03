#!/bin/sh
set -e

echo "=== Running tests ==="
pytest -v
echo "=== Tests passed. Starting server ==="

exec uvicorn app.main:app --host 0.0.0.0 --port 8000