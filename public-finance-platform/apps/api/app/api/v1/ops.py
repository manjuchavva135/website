from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.observability import metrics_registry
from app.db.session import get_db
from app.models import ParserError, ParserRun, SourceFetchRun

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics(db: Session = Depends(get_db)) -> PlainTextResponse:
    lines = [metrics_registry.render_prometheus().rstrip()]

    parser_errors = db.execute(
        select(ParserError.error_level, func.count()).group_by(ParserError.error_level)
    ).all()
    lines.extend(
        [
            "# HELP parser_anomalies_total Parser warnings/errors/fatals persisted by level.",
            "# TYPE parser_anomalies_total gauge",
        ]
    )
    for level, count in parser_errors:
        lines.append(f'parser_anomalies_total{{level="{level}"}} {int(count)}')

    parser_runs = db.execute(select(ParserRun.status, func.count()).group_by(ParserRun.status)).all()
    lines.extend(
        [
            "# HELP parser_runs_total Parser runs by status.",
            "# TYPE parser_runs_total gauge",
        ]
    )
    for status, count in parser_runs:
        lines.append(f'parser_runs_total{{status="{status}"}} {int(count)}')

    fetch_runs = db.execute(select(SourceFetchRun.status, func.count()).group_by(SourceFetchRun.status)).all()
    lines.extend(
        [
            "# HELP source_fetch_runs_total Source fetch runs by status.",
            "# TYPE source_fetch_runs_total gauge",
        ]
    )
    for status, count in fetch_runs:
        lines.append(f'source_fetch_runs_total{{status="{status}"}} {int(count)}')

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@router.get("/parser-anomalies")
def parser_anomalies(db: Session = Depends(get_db)) -> dict[str, object]:
    levels = {
        str(level): int(count)
        for level, count in db.execute(
            select(ParserError.error_level, func.count()).group_by(ParserError.error_level)
        ).all()
    }
    failed_runs = db.scalar(select(func.count()).select_from(ParserRun).where(ParserRun.status == "failed")) or 0
    fatal_errors = levels.get("fatal", 0)
    warning_count = levels.get("warning", 0)
    severity = "critical" if fatal_errors or failed_runs else "warning" if warning_count else "ok"
    return {
        "severity": severity,
        "levels": levels,
        "failed_parser_runs": int(failed_runs),
        "alertable": severity != "ok",
    }
