from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from worker.config import settings


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
            "event": getattr(record, "event", None),
        }
        context = getattr(record, "context", None)
        if context is not None:
            payload["context"] = context
        return json.dumps({key: value for key, value in payload.items() if value is not None}, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


logger = logging.getLogger("public_finance.worker")


def emit_parser_anomaly(
    *,
    source_name: str,
    anomaly_type: str,
    severity: str,
    message: str,
    context: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    event = {
        "source_name": source_name,
        "anomaly_type": anomaly_type,
        "severity": severity,
        "message": message,
        "context": context or {},
        "correlation_id": correlation_id or str(uuid4()),
    }
    logger.warning(
        "parser_anomaly",
        extra={
            "event": "parser_anomaly",
            "context": event,
            "correlation_id": event["correlation_id"],
        },
    )
    return event


def report_summary_anomalies(
    *,
    source_name: str,
    summary: dict[str, Any],
    correlation_id: str | None = None,
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    warning_count = int(summary.get("warning_count") or summary.get("warnings_count") or 0)
    manual_review_count = int(summary.get("manual_review_count") or 0)
    status = str(summary.get("status", "ok"))

    if status not in {"ok", "succeeded"}:
        anomalies.append(
            emit_parser_anomaly(
                source_name=source_name,
                anomaly_type="task_status",
                severity="critical",
                message=f"Ingestion task returned status {status}",
                context=summary,
                correlation_id=correlation_id,
            )
        )
    if warning_count >= settings.parser_anomaly_warning_threshold:
        anomalies.append(
            emit_parser_anomaly(
                source_name=source_name,
                anomaly_type="warning_threshold",
                severity="warning",
                message=f"Parser warnings reached {warning_count}",
                context=summary,
                correlation_id=correlation_id,
            )
        )
    if manual_review_count >= settings.parser_anomaly_manual_review_threshold:
        anomalies.append(
            emit_parser_anomaly(
                source_name=source_name,
                anomaly_type="manual_review_threshold",
                severity="warning",
                message=f"Manual review count reached {manual_review_count}",
                context=summary,
                correlation_id=correlation_id,
            )
        )
    return anomalies
