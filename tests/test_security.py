"""Tests for the DevOps/security hardening: health, headers, rate limit, secret."""

from __future__ import annotations

import pytest

from vigil.config import DEFAULT_SECRET, Settings


def test_health_is_public(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert "max-age" in r.headers["Strict-Transport-Security"]


def test_auth_rate_limited(client, monkeypatch):
    # Tighten the limit via env (read fresh by get_settings on each request).
    monkeypatch.setenv("VIGIL_AUTH_MAX_ATTEMPTS", "3")
    seen_429 = False
    for _ in range(6):
        r = client.post("/api/login", json={"username": "x", "password": "y"})
        if r.status_code == 429:
            seen_429 = True
            break
    assert seen_429, "login endpoint should rate-limit repeated attempts"


def test_production_requires_real_secret():
    # Default, empty, and too-short secrets all fail in production.
    for bad in (DEFAULT_SECRET, "", "short"):
        with pytest.raises(RuntimeError):
            Settings(env="production", secret_key=bad).check_security()

    # A strong secret in production is fine; the default in development is allowed.
    Settings(env="production", secret_key="a-properly-long-secret-value").check_security()
    Settings(env="development", secret_key=DEFAULT_SECRET).check_security()
