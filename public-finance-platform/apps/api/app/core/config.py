import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, list):
            return [str(item).strip() for item in decoded if str(item).strip()]
        return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def _normalize_database_url(value: Any) -> str:
    raw = str(value)
    if raw.startswith("postgres://"):
        return f"postgresql+psycopg://{raw.removeprefix('postgres://')}"
    if raw.startswith("postgresql://"):
        return f"postgresql+psycopg://{raw.removeprefix('postgresql://')}"
    return raw


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_path: str = "/api/v1"
    auto_create_schema: bool = True
    auto_seed_data: bool = True
    parser_version: str = "2026.04.24"
    admin_api_token: str = "dev-admin-token"
    admin_allowed_emails: Any = ["admin@apfinance.local"]

    cors_origins: Any = ["http://localhost:3000"]

    database_url: str = Field(default="sqlite:///./public_finance.db")

    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    dispatch_admin_parser_jobs: bool = False
    log_level: str = "INFO"
    public_api_rate_limit_per_minute: int = 600
    public_api_rate_limit_enabled: bool = True
    public_cache_max_age_seconds: int = 60
    cdn_cache_s_maxage_seconds: int = 300
    csv_cache_max_age_seconds: int = 300
    csv_cdn_cache_s_maxage_seconds: int = 1800

    s3_endpoint_url: str = Field(...)
    s3_region: str = "us-east-1"
    s3_bucket: str = Field(...)
    s3_access_key: str = Field(...)
    s3_secret_key: str = Field(...)
    s3_use_ssl: bool = False

    rbi_source_url: str = "https://rbi.org.in/"
    ap_finance_source_url: str = "https://finance.ap.gov.in/"
    cag_source_url: str = "https://cag.gov.in/"

    @field_validator("admin_allowed_emails", "cors_origins")
    @classmethod
    def parse_string_lists(cls, value: Any) -> list[str]:
        return _parse_string_list(value)

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: Any) -> str:
        return _normalize_database_url(value)


settings = Settings()
