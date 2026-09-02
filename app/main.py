"""MoneyOS — FastAPI app. Mounts service routers and inits DB on startup."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from service.api import (  # noqa: E402
    agent_router,
    approval_router,
    audit_router,
    catalog_router,
    checkout_page_router,
    checkout_router,
    settings_router,
    webhooks_router,
)
from service.db import init_db  # noqa: E402

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables. Shutdown: nothing special."""
    init_db()
    yield


app = FastAPI(
    title="MoneyOS",
    version="0.1.0",
    description="AI-powered merchant agent with ACP checkout endpoints on Razorpay test mode",
    lifespan=lifespan,
)

app.include_router(agent_router)
app.include_router(approval_router)
app.include_router(audit_router)
app.include_router(catalog_router)
app.include_router(checkout_router)
app.include_router(checkout_page_router)
app.include_router(settings_router)
app.include_router(webhooks_router)
app.include_router(audit_router)


@app.get("/health")
def health():
    return {"status": "ok"}


if FRONTEND_DIR.is_dir():
    app.frontend("/", directory=str(FRONTEND_DIR), fallback="index.html")
