from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "development"
    parser_version: str = "2026.04.24"
    database_url: str = "postgresql+psycopg://public_finance:public_finance@postgres:5432/public_finance"

    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    s3_endpoint_url: str = "http://minio:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "public-finance-data"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
    s3_use_ssl: bool = False

    rbi_source_url: str = "https://rbi.org.in/"
    ap_finance_source_url: str = "https://finance.ap.gov.in/"
    cag_source_url: str = "https://cag.gov.in/"
    log_level: str = "INFO"
    idempotency_lock_ttl_seconds: int = 86400
    parser_anomaly_warning_threshold: int = 10
    parser_anomaly_manual_review_threshold: int = 1


settings = WorkerSettings()
