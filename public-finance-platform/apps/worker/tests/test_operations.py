from worker.commands.backfill import build_backfill_plan
from worker.health import worker_health
from worker.idempotency import stable_job_key
from worker.observability import report_summary_anomalies


def test_stable_job_key_is_deterministic() -> None:
    first = stable_job_key("task.name", {"b": 2, "a": 1})
    second = stable_job_key("task.name", {"a": 1, "b": 2})

    assert first == second
    assert first.startswith("task.name:")


def test_backfill_plan_uses_deterministic_task_ids() -> None:
    first = build_backfill_plan(
        source="ap_finance",
        from_date="2020-04-01",
        to_date="2021-03-31",
        force=False,
    )
    second = build_backfill_plan(
        source="ap_finance",
        from_date="2020-04-01",
        to_date="2021-03-31",
        force=False,
    )

    assert first == second
    assert first[0]["task_name"] == "worker.tasks.ap_finance_ingest.fetch_ap_finance_data"
    assert first[0]["kwargs"]["idempotency_key"] == first[0]["task_id"]


def test_worker_health_without_external_checks() -> None:
    payload = worker_health(check_external=False)

    assert payload["service"] == "worker"
    assert payload["status"] == "ok"
    assert payload["checks"]["configuration"] == "ok"


def test_parser_anomaly_reporting_for_manual_review() -> None:
    anomalies = report_summary_anomalies(
        source_name="ap_finance",
        summary={"status": "ok", "warning_count": 0, "manual_review_count": 1},
        correlation_id="test-key",
    )

    assert len(anomalies) == 1
    assert anomalies[0]["anomaly_type"] == "manual_review_threshold"
    assert anomalies[0]["correlation_id"] == "test-key"
