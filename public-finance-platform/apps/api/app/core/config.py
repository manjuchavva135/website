from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    auto_seed_data: bool = True
    parser_version: str = "2026.04.24"
    admin_api_token: str = "dev-admin-token"
    admin_allowed_emails: list[str] = ["admin@apfinance.local"]

    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = Field(
        default="sqlite:///./public_finance.db"
    )

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

    s3_endpoint_url: str = "http://minio:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "public-finance-data"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
    s3_use_ssl: bool = False

    rbi_source_url: str = "https://rbi.org.in/"
    ap_finance_source_url: str = "https://finance.ap.gov.in/"
    cag_source_url: str = "https://cag.gov.in/"


settings = Settings()
