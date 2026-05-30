"""Shared fixtures: an in-memory DB, a TestClient, and a mock-HTTP helper.

Everything runs offline — HTTP checks are served by httpx.MockTransport through
apikit, so no real network requests are ever made.
"""

from __future__ import annotations

import httpx
import pytest
from apikit import ApiClient, NO_RETRIES
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from vigil.app import app
from vigil.db import get_session
from vigil.models import Monitor, User
from vigil.security import hash_password


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)   # no `with` -> skip startup init_db side effects
    app.dependency_overrides.clear()


@pytest.fixture
def user(session) -> User:
    u = User(username="alice", password_hash=hash_password("pw"))
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


@pytest.fixture
def monitor(session, user) -> Monitor:
    m = Monitor(owner_id=user.id, name="Example", url="https://example.com",
                expected_status=200)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def make_http(handler) -> ApiClient:
    """An apikit client backed by a MockTransport handler (no retries/backoff)."""
    return ApiClient(
        client=httpx.Client(base_url="https://mock.test", transport=httpx.MockTransport(handler)),
        raise_for_status=False, retry=NO_RETRIES,
    )


@pytest.fixture
def auth_headers(client):
    """Register a fresh user via the API and return Bearer auth headers."""
    def _make(username="bob", password="secret"):
        token = client.post("/api/register",
                            json={"username": username, "password": password}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return _make
