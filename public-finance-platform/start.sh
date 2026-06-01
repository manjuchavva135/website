#!/usr/bin/env bash
# Start all public-finance-platform services locally (PostgreSQL backend).
# Run from the public-finance-platform/ directory.
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv/bin"
PYTHONPATH="$ROOT/apps/worker:$ROOT/apps/api:$ROOT/packages/shared-py"
export PYTHONPATH

echo "▶ Starting PostgreSQL..."
sudo systemctl start postgresql redis-server 2>/dev/null || true
sleep 1

echo "▶ Starting API (port 8000)..."
cd "$ROOT/apps/api"
"$VENV/uvicorn" app.main:app --host 0.0.0.0 --port 8000 >> /tmp/api.log 2>&1 &
echo "  API PID=$!"

echo "▶ Starting Celery Worker..."
cd "$ROOT/apps/worker"
"$VENV/celery" -A worker.celery_app worker --loglevel=info >> /tmp/worker.log 2>&1 &
echo "  Worker PID=$!"

echo "▶ Starting Next.js Frontend (port 3000)..."
cd "$ROOT/apps/web"
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 node_modules/.bin/next start -p 3000 >> /tmp/web.log 2>&1 &
echo "  Web PID=$!"

sleep 4
echo ""
echo "=========================================="
echo "  Services running:"
echo "  Frontend  → http://localhost:3000"
echo "  API       → http://localhost:8000/api/v1"
echo "  API Docs  → http://localhost:8000/docs"
echo "  Admin     → http://localhost:3000/admin"
echo "=========================================="
echo ""
echo "  Log files:"
echo "  tail -f /tmp/api.log"
echo "  tail -f /tmp/worker.log"
echo "  tail -f /tmp/web.log"
