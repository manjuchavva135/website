#!/bin/bash
# AP Finance Platform - Startup Script
# Starts API, Next.js web, and ngrok on boot via crontab @reboot
# Logs go to /tmp/ap-finance-*.log

set -a
PLATFORM="/home/maveric2/website/public-finance-platform"
LOG_DIR="/tmp"

# Wait for network and PostgreSQL to be ready
sleep 15

# Load environment
source "$PLATFORM/.env" 2>/dev/null || true

# Kill any leftover processes from previous runs
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
pkill -f "ngrok http 3000" 2>/dev/null || true
sleep 2

# --- Start API ---
cd "$PLATFORM"
PYTHONPATH="$PLATFORM/apps/api" \
  "$PLATFORM/.venv/bin/uvicorn" app.main:app \
  --app-dir apps/api \
  --host 0.0.0.0 \
  --port 8000 \
  >> "$LOG_DIR/ap-finance-api.log" 2>&1 &
echo "API started (PID $!)" >> "$LOG_DIR/ap-finance-startup.log"

# --- Start Next.js web ---
cd "$PLATFORM/apps/web"
/usr/local/bin/pnpm dev \
  >> "$LOG_DIR/ap-finance-web.log" 2>&1 &
echo "Web started (PID $!)" >> "$LOG_DIR/ap-finance-startup.log"

# Wait for web to be ready before starting ngrok
sleep 20

# --- Start ngrok ---
/usr/local/bin/ngrok http 3000 --log=stdout \
  >> "$LOG_DIR/ap-finance-ngrok.log" 2>&1 &
echo "ngrok started (PID $!)" >> "$LOG_DIR/ap-finance-startup.log"

echo "All services started at $(date)" >> "$LOG_DIR/ap-finance-startup.log"
