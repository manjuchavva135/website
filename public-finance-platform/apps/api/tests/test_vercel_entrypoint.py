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


def test_settings_accept_vercel_plain_string_list_envs() -> None:
    app_dir = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "ADMIN_ALLOWED_EMAILS": "admin@example.gov.in",
        "CORS_ORIGINS": "https://andhra-finance.vercel.app",
    }
    code = (
        "from app.core.config import Settings;"
        "settings = Settings();"
        "assert settings.admin_allowed_emails == ['admin@example.gov.in'];"
        "assert settings.cors_origins == ['https://andhra-finance.vercel.app']"
    )

    subprocess.run([sys.executable, "-c", code], cwd=app_dir, env=env, check=True)


def test_vercel_db_backed_route_returns_json_when_database_missing() -> None:
    app_dir = Path(__file__).resolve().parents[1]
    missing_db = app_dir / "missing_vercel_route_test.db"
    if missing_db.exists():
        missing_db.unlink()
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{missing_db.as_posix()}",
        "AUTO_CREATE_SCHEMA": "false",
        "AUTO_SEED_DATA": "false",
    }
    code = (
        "from fastapi.testclient import TestClient;"
        "from vercel_app import app;"
        "client = TestClient(app);"
        "response = client.get('/v1/sources');"
        "assert response.status_code == 503;"
        "payload = response.json();"
        "assert payload['detail'] == 'Database unavailable or schema missing';"
        "assert response.headers['X-Correlation-ID']"
    )

    try:
        subprocess.run([sys.executable, "-c", code], cwd=app_dir, env=env, check=True)
    finally:
        if missing_db.exists():
            missing_db.unlink()
