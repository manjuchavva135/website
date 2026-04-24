from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_engine
from app.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        service="api",
        status="ok",
        environment=settings.env,
    )


@router.get("/live")
def liveness() -> dict[str, str]:
    return {
        "service": "api",
        "status": "ok",
        "environment": settings.env,
    }


@router.get("/ready")
def readiness() -> dict[str, object]:
    checks: dict[str, str] = {}
    status = "ok"
    try:
        with get_engine().connect() as connection:
            connection.execute(text("select 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        status = "degraded"

    return {
        "service": "api",
        "status": status,
        "environment": settings.env,
        "checks": checks,
    }
