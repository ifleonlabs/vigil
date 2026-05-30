"""Tests for the check engine — every HTTP call goes through a mock transport."""

from __future__ import annotations

import httpx
from notifykit import Level, MemoryChannel, Notifier

from vigil import notify
from vigil.checks import perform_check, record_check, run_check
from vigil.models import CheckStatus, Incident, Monitor
from vigil.stats import open_incident_count

from conftest import make_http


def ok(body="hello world"):
    return lambda r: httpx.Response(200, text=body)


# --- perform_check (pure, no DB) -----------------------------------------
def test_up_when_status_matches():
    m = Monitor(owner_id=1, name="x", url="https://x", expected_status=200)
    outcome = perform_check(m, make_http(ok()))
    assert outcome.status is CheckStatus.UP
    assert outcome.status_code == 200
    assert outcome.latency_ms is not None and outcome.body_hash is not None


def test_down_on_wrong_status():
    m = Monitor(owner_id=1, name="x", url="https://x", expected_status=200)
    outcome = perform_check(m, make_http(lambda r: httpx.Response(500)))
    assert outcome.status is CheckStatus.DOWN
    assert "500" in outcome.error


def test_down_when_keyword_missing():
    m = Monitor(owner_id=1, name="x", url="https://x", keyword="welcome")
    outcome = perform_check(m, make_http(ok("goodbye")))
    assert outcome.status is CheckStatus.DOWN
    assert "welcome" in outcome.error


def test_up_when_keyword_present():
    m = Monitor(owner_id=1, name="x", url="https://x", keyword="hello")
    assert perform_check(m, make_http(ok("hello there"))).status is CheckStatus.UP


def test_down_on_connection_error():
    def boom(request):
        raise httpx.ConnectError("refused", request=request)

    m = Monitor(owner_id=1, name="x", url="https://x")
    outcome = perform_check(m, make_http(boom))
    assert outcome.status is CheckStatus.DOWN
    assert outcome.status_code is None


def test_content_change_detection():
    m = Monitor(owner_id=1, name="x", url="https://x", watch_content=True)
    # First check establishes a baseline -> UP, hash recorded.
    first = perform_check(m, make_http(ok("v1")))
    assert first.status is CheckStatus.UP
    # Pretend that baseline was stored; a different body now reads as CHANGED.
    m.last_body_hash = first.body_hash
    changed = perform_check(m, make_http(ok("v2-different")))
    assert changed.status is CheckStatus.CHANGED


# --- record_check (DB + incidents) ---------------------------------------
def test_record_advances_monitor_state(session, monitor):
    check = run_check(session, monitor, client=make_http(ok()))
    assert check.status is CheckStatus.UP
    assert monitor.last_status is CheckStatus.UP
    assert monitor.last_checked_at is not None
    assert monitor.next_check_at > monitor.last_checked_at


def test_incident_opens_on_down_and_resolves_on_up(session, monitor):
    run_check(session, monitor, client=make_http(lambda r: httpx.Response(503)))
    assert open_incident_count(session, monitor.id) == 1

    run_check(session, monitor, client=make_http(ok()))
    assert open_incident_count(session, monitor.id) == 0
    # The incident row persists but is now resolved.
    incidents = session.exec(__import__("sqlmodel").select(Incident)).all()
    assert len(incidents) == 1 and incidents[0].resolved_at is not None


def test_repeated_down_does_not_open_duplicate_incidents(session, monitor):
    down = lambda r: httpx.Response(500)  # noqa: E731
    run_check(session, monitor, client=make_http(down))
    run_check(session, monitor, client=make_http(down))
    assert open_incident_count(session, monitor.id) == 1


# --- alerting via notifykit ----------------------------------------------
def test_incident_open_and_resolve_send_alerts(session, monitor, monkeypatch):
    monitor.webhook_url = "https://hook.test"
    session.add(monitor)
    session.commit()

    mem = MemoryChannel()
    monkeypatch.setattr(notify, "build_notifier", lambda url: Notifier(mem))

    run_check(session, monitor, client=make_http(lambda r: httpx.Response(500)))
    assert mem.last.level is Level.ERROR and "DOWN" in mem.last.title

    run_check(session, monitor, client=make_http(lambda r: httpx.Response(200, text="hi")))
    assert mem.last.level is Level.SUCCESS and "RECOVERED" in mem.last.title


def test_no_alert_without_webhook_url(session, monitor, monkeypatch):
    called = []
    monkeypatch.setattr(notify, "build_notifier", lambda url: called.append(url) or Notifier())
    run_check(session, monitor, client=make_http(lambda r: httpx.Response(500)))
    assert called == []   # monitor has no webhook_url -> no notifier built
