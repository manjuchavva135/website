import os
import subprocess
import sys
from pathlib import Path


def test_vercel_entrypoint_mounts_api_after_service_prefix_strip() -> None:
    app_dir = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite:///:memory:",
        "AUTO_CREATE_SCHEMA": "false",
        "AUTO_SEED_DATA": "false",
    }
    code = (
        "from fastapi.testclient import TestClient;"
        "from vercel_app import app;"
        "client = TestClient(app);"
        "assert client.get('/v1/health').status_code == 200;"
        "assert client.get('/api/v1/health').status_code == 404"
    )

    subprocess.run([sys.executable, "-c", code], cwd=app_dir, env=env, check=True)
