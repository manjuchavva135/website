param(
  [switch]$InstallNode,
  [switch]$InstallPython
)

$ErrorActionPreference = "Stop"

Copy-Item .env.example .env -ErrorAction SilentlyContinue

if ($InstallNode) {
  corepack enable
  pnpm install
}

if ($InstallPython) {
  python -m pip install -r requirements-dev.txt
  python -m pip install -r apps/api/requirements.txt
  python -m pip install -r apps/worker/requirements.txt
  python -m pip install -e packages/shared-py
}

Write-Host "Bootstrap complete."
