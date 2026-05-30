"""API tests via FastAPI TestClient — auth, monitor CRUD, ownership, check-now."""

from __future__ import annotations

import httpx

from vigil import app as app_module
from vigil.models import CheckStatus

from conftest import make_http


def test_register_and_login(client):
    r = client.post("/api/register", json={"username": "alice", "password": "pw"})
    assert r.status_code == 200 and r.json()["username"] == "alice"
    assert client.post("/api/login", json={"username": "alice", "password": "pw"}).status_code == 200
    assert client.post("/api/login", json={"username": "alice", "password": "no"}).status_code == 401


def test_duplicate_registration_conflicts(client):
    client.post("/api/register", json={"username": "alice", "password": "pw"})
    r = client.post("/api/register", json={"username": "alice", "password": "pw"})
    assert r.status_code == 409


def test_monitors_require_auth(client):
    assert client.get("/api/monitors").status_code == 401


def test_create_and_list_monitor(client, auth_headers):
    headers = auth_headers()
    r = client.post("/api/monitors", headers=headers,
                    json={"name": "Site", "url": "https://example.com", "interval_seconds": 60})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Site" and body["last_status"] is None

    listing = client.get("/api/monitors", headers=headers).json()
    assert len(listing) == 1 and listing[0]["url"] == "https://example.com"


def test_monitors_are_per_user(client, auth_headers):
    a = auth_headers("alice")
    b = auth_headers("bob")
    mid = client.post("/api/monitors", headers=a,
                      json={"name": "A", "url": "https://a"}).json()["id"]
    # Bob cannot see or fetch Alice's monitor.
    assert client.get("/api/monitors", headers=b).json() == []
    assert client.get(f"/api/monitors/{mid}", headers=b).status_code == 404


def test_update_and_delete_monitor(client, auth_headers):
    headers = auth_headers()
    mid = client.post("/api/monitors", headers=headers,
                      json={"name": "S", "url": "https://s"}).json()["id"]

    paused = client.patch(f"/api/monitors/{mid}", headers=headers, json={"paused": True}).json()
    assert paused["paused"] is True

    assert client.delete(f"/api/monitors/{mid}", headers=headers).status_code == 204
    assert client.get("/api/monitors", headers=headers).json() == []


def test_check_now_runs_synchronously(client, auth_headers, monkeypatch):
    headers = auth_headers()
    mid = client.post("/api/monitors", headers=headers,
                      json={"name": "S", "url": "https://s", "expected_status": 200}).json()["id"]

    # Patch the check engine's client factory so the endpoint uses a mock transport.
    monkeypatch.setattr(app_module, "build_client",
                        lambda *a, **k: make_http(lambda r: httpx.Response(200, text="ok")))

    r = client.post(f"/api/monitors/{mid}/check", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == CheckStatus.UP.value

    # The monitor now reflects the check in its summary.
    summary = client.get(f"/api/monitors/{mid}", headers=headers).json()
    assert summary["last_status"] == CheckStatus.UP.value
    assert summary["uptime_ratio"] == 1.0
    assert len(summary["recent_checks"]) == 1


def test_dashboard_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "vigil" in r.text.lower()
