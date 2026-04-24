from worker.config import settings


def test_worker_has_broker_url() -> None:
    assert settings.celery_broker_url.startswith("redis://")
