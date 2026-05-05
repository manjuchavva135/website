from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(value: Any) -> str:
    raw = str(value)
    if raw.startswith("postgres://"):
        return f"postgresql+psycopg://{raw.removeprefix('postgres://')}"
    if raw.startswith("postgresql://"):
        return f"postgresql+psycopg://{raw.removeprefix('postgresql://')}"
    return raw


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "development"
    parser_version: str = "2026.04.24"
    database_url: str = "postgresql+psycopg://public_finance:public_finance@postgres:5432/public_finance"

    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    s3_endpoint_url: str = Field(...)
    s3_region: str = "us-east-1"
    s3_bucket: str = Field(...)
    s3_access_key: str = Field(...)
    s3_secret_key: str = Field(...)
    s3_use_ssl: bool = False

    rbi_source_url: str = "https://rbi.org.in/"
    ap_finance_source_url: str = "https://finance.ap.gov.in/"
    cag_source_url: str = "https://cag.gov.in/"
    log_level: str = "INFO"
    idempotency_lock_ttl_seconds: int = 86400
    parser_anomaly_warning_threshold: int = 10
    parser_anomaly_manual_review_threshold: int = 1

    # Set to True after baseline-v1 is published to re-enable weekly auto-fetchers.
    auto_fetchers_enabled: bool = False

    # Extractor to use for manual uploads. Options: rule_based | llm | hybrid.
    extractor_provider: str = "rule_based"

    @field_validator("s3_endpoint_url", "s3_bucket", "s3_access_key", "s3_secret_key")
    @classmethod
    def require_non_empty_s3_config(cls, value: Any) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("must be set to a non-empty value")
        return normalized

    @field_validator("database_url")
    @classmethod
    def normalize_hosted_postgres_url(cls, value: Any) -> str:
        return normalize_database_url(value)


settings = WorkerSettings()
