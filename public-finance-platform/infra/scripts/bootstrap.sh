#!/usr/bin/env bash
set -euo pipefail

cp -n .env.example .env || true

if [[ "${1:-}" == "--install-node" ]]; then
  corepack enable
  pnpm install
fi

if [[ "${2:-}" == "--install-python" || "${1:-}" == "--install-python" ]]; then
  python -m pip install -r requirements-dev.txt
  python -m pip install -r apps/api/requirements.txt
  python -m pip install -r apps/worker/requirements.txt
  python -m pip install -e packages/shared-py
fi

echo "Bootstrap complete."
