from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_metrics_series_available(client: TestClient) -> None:
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 10
    assert any(item["metric_group"] == "debt_outstanding" for item in payload)


def test_metrics_observations_do_not_mix_unlabeled_basis(client: TestClient) -> None:
    response = client.get("/api/v1/metrics/ap-outstanding-debt/observations?basis=budget_estimate")
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert all(item["basis"] == "budget_estimate" for item in payload)


def test_metrics_csv_download(client: TestClient) -> None:
    response = client.get("/api/v1/metrics/ap-outstanding-debt/observations.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert "series_slug" in body


def test_review_queue_endpoint_exists(client: TestClient) -> None:
    response = client.get(
        "/api/v1/admin/review-queue",
        headers={
            "X-Admin-Email": settings.admin_allowed_emails[0],
            "X-Admin-Token": settings.admin_api_token,
        },
    )
    assert response.status_code == 200
