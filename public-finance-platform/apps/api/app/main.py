from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.ap_overview import router as ap_overview_router
from app.api.v1.changelog import router as changelog_router
from app.api.v1.debt_stack import router as debt_stack_router
from app.api.v1.health import router as health_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.ops import router as ops_router
from app.api.v1.peers import router as peers_router
from app.api.v1.provenance import router as provenance_router
from app.api.v1.public_finance import router as public_finance_router
from app.api.v1.review import router as review_router
from app.core.config import settings
from app.core.observability import configure_logging, install_observability
from app.db.bootstrap import create_schema, seed_reference_data
from app.db.session import SessionLocal

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_schema:
        create_schema()
    if settings.auto_seed_data:
        with SessionLocal() as db:
            seed_reference_data(db)
    yield


app = FastAPI(title="Public Finance API", version="0.1.0", lifespan=lifespan)
install_observability(app)

api_prefix = settings.api_base_path.rstrip("/")
if api_prefix == "/":
    api_prefix = ""

app.include_router(health_router, prefix=api_prefix)
app.include_router(metrics_router, prefix=api_prefix)
app.include_router(ops_router, prefix=api_prefix)
app.include_router(public_finance_router, prefix=api_prefix)
app.include_router(ap_overview_router, prefix=api_prefix)
app.include_router(debt_stack_router, prefix=api_prefix)
app.include_router(peers_router, prefix=api_prefix)
app.include_router(provenance_router, prefix=api_prefix)
app.include_router(review_router, prefix=api_prefix)
app.include_router(changelog_router, prefix=api_prefix)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Public Finance API",
        "env": settings.env,
    }
