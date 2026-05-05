import pytest

from worker.celery_app import TASK_MODULES, celery_app
from worker.config import settings
from worker.config import WorkerSettings


def test_worker_has_broker_url() -> None:
    assert settings.celery_broker_url.startswith("redis://")


def test_worker_registers_expected_tasks() -> None:
    for module_name in TASK_MODULES:
        assert module_name in celery_app.conf.include

    assert "worker.tasks.ap_finance_ingest.fetch_ap_finance_data" in celery_app.tasks
    assert "worker.tasks.rbi_ingest.fetch_rbi_borrowing_data" in celery_app.tasks


def test_worker_requires_non_empty_s3_bucket() -> None:
    with pytest.raises(ValueError, match="s3_bucket"):
        WorkerSettings(
            s3_endpoint_url="https://example-s3.test",
            s3_bucket=" ",
            s3_access_key="test-key",
            s3_secret_key="test-secret",
        )
