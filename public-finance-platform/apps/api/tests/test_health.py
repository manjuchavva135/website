from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.observability import CORRELATION_ID_HEADER, metrics_registry, rate_limiter
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "api"
    assert payload["status"] == "ok"


def test_correlation_id_is_echoed(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={CORRELATION_ID_HEADER: "test-correlation"})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == "test-correlation"


def test_readiness_and_prometheus_metrics(client: TestClient) -> None:
    metrics_registry.reset()
    client.get("/api/v1/health")

    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] == "ok"

    metrics = client.get("/api/v1/ops/metrics")
    assert metrics.status_code == 200
    assert "http_requests_total" in metrics.text
    assert "parser_anomalies_total" in metrics.text


def test_parser_anomaly_summary_shape(client: TestClient) -> None:
    response = client.get("/api/v1/ops/parser-anomalies")

    assert response.status_code == 200
    payload = response.json()
    assert "severity" in payload
    assert "alertable" in payload


def test_public_api_rate_limiting(client: TestClient) -> None:
    previous_limit = settings.public_api_rate_limit_per_minute
    previous_enabled = settings.public_api_rate_limit_enabled
    settings.public_api_rate_limit_per_minute = 1
    settings.public_api_rate_limit_enabled = True
    rate_limiter.reset()
    try:
        first = client.get("/api/v1/sources?page_size=1")
        second = client.get("/api/v1/sources?page_size=1")
        assert first.status_code == 200
        assert second.status_code == 429
        assert second.headers["Retry-After"] == "60"
    finally:
        settings.public_api_rate_limit_per_minute = previous_limit
        settings.public_api_rate_limit_enabled = previous_enabled
        rate_limiter.reset()
