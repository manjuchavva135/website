from worker.config import WorkerSettings
from worker.health import worker_health
from worker.idempotency import stable_job_key
from worker.observability import report_summary_anomalies


def test_stable_job_key_is_deterministic() -> None:
    first = stable_job_key("task.name", {"b": 2, "a": 1})
    second = stable_job_key("task.name", {"a": 1, "b": 2})

    assert first == second
    assert first.startswith("task.name:")


def test_worker_health_without_external_checks() -> None:
    payload = worker_health(check_external=False)

    assert payload["service"] == "worker"
    assert payload["status"] == "ok"
    assert payload["checks"]["configuration"] == "ok"


def test_worker_settings_normalizes_hosted_postgres_url() -> None:
    s = WorkerSettings(database_url="postgresql://user:pass@example.com/db?sslmode=require")

    assert s.database_url.startswith("postgresql+psycopg://")


def test_parser_anomaly_reporting_for_manual_review() -> None:
    anomalies = report_summary_anomalies(
        source_name="rbi_auction",
        summary={"status": "ok", "warning_count": 0, "manual_review_count": 1},
        correlation_id="test-key",
    )

    assert len(anomalies) == 1
    assert anomalies[0]["anomaly_type"] == "manual_review_threshold"
    assert anomalies[0]["correlation_id"] == "test-key"
