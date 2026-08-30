"""Shared test fixtures — one in-memory SQLite DB across all threads."""

import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure app/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service.db.connection import Base, get_db
from service.db.models import AuditLog  # noqa: F401 — registers table with Base

# Shared engine using StaticPool so all threads share one in-memory SQLite connection.
# This is essential because FastAPI TestClient runs endpoint handlers in worker threads.
_test_engine = create_engine(
    "sqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_test_engine)
_TestSession = sessionmaker(bind=_test_engine)


@pytest.fixture
def db_session():
    """Yield a DB session for unit tests."""
    session = _TestSession()
    yield session
    session.close()


@pytest.fixture
def client():
    """Yield a TestClient with DB dependency overridden."""
    from service.api import audit_router, catalog_router, checkout_router

    app = FastAPI()
    app.include_router(catalog_router)
    app.include_router(checkout_router)
    app.include_router(audit_router)

    def override_get_db():
        db = _TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
