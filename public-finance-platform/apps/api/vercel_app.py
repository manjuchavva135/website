import os

os.environ["API_BASE_PATH"] = os.environ.get("VERCEL_API_BASE_PATH", "/v1")
os.environ["AUTO_CREATE_SCHEMA"] = os.environ.get("VERCEL_AUTO_CREATE_SCHEMA", "false")
os.environ["AUTO_SEED_DATA"] = os.environ.get("VERCEL_AUTO_SEED_DATA", "false")

from app.main import app  # noqa: E402,F401
