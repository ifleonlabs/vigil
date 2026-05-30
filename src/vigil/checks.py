"""The check engine: fetch a monitor's URL with apikit and record the result.

This is where the engine parts earn their keep — every check is an ``apikit``
request (timeout + retry/backoff for free), and the outcome is reduced to one
of UP / DOWN / CHANGED, then persisted along with incident bookkeeping.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from apikit import ApiClient, RetryPolicy
from apikit.errors import ApiError
from sqlmodel import Session

from . import notify
from .config import Settings, get_settings
from .models import Check, CheckStatus, Incident, Monitor, utcnow


@dataclass
class CheckOutcome:
    status: CheckStatus
    status_code: int | None = None
    latency_ms: float | None = None
    error: str | None = None
    body_hash: str | None = None


def build_client(settings: Settings | None = None, *, client: ApiClient | None = None) -> ApiClient:
    """An apikit client tuned for checks. Pass ``client`` to inject one in tests."""
    if client is not None:
        return client
    settings = settings or get_settings()
    return ApiClient(
        timeout=settings.check_timeout,
        retry=RetryPolicy(max_retries=settings.check_retries),
        raise_for_status=False,   # we inspect the status ourselves
    )


def perform_check(monitor: Monitor, client: ApiClient) -> CheckOutcome:
    """Fetch the monitor's URL and classify the result. No DB access."""
    start = time.monotonic()
    try:
        response = client.get(monitor.url)
    except ApiError as exc:
        latency = (time.monotonic() - start) * 1000
        return CheckOutcome(CheckStatus.DOWN, latency_ms=latency, error=str(exc))

    latency = (time.monotonic() - start) * 1000
    body_hash = hashlib.sha256(response.content).hexdigest()

    if response.status_code != monitor.expected_status:
        return CheckOutcome(CheckStatus.DOWN, status_code=response.status_code,
                            latency_ms=latency, body_hash=body_hash,
                            error=f"expected {monitor.expected_status}, got {response.status_code}")

    if monitor.keyword and monitor.keyword not in response.text:
        return CheckOutcome(CheckStatus.DOWN, status_code=response.status_code,
                            latency_ms=latency, body_hash=body_hash,
                            error=f"keyword {monitor.keyword!r} not found")

    if (monitor.watch_content and monitor.last_body_hash is not None
            and body_hash != monitor.last_body_hash):
        return CheckOutcome(CheckStatus.CHANGED, status_code=response.status_code,
                            latency_ms=latency, body_hash=body_hash)

    return CheckOutcome(CheckStatus.UP, status_code=response.status_code,
                        latency_ms=latency, body_hash=body_hash)


def record_check(session: Session, monitor: Monitor, outcome: CheckOutcome,
                 *, now: datetime | None = None) -> Check:
    """Persist a check, advance the monitor's state, and open/resolve incidents."""
    now = now or utcnow()

    check = Check(
        monitor_id=monitor.id,
        status=outcome.status,
        status_code=outcome.status_code,
        latency_ms=outcome.latency_ms,
        error=outcome.error,
        checked_at=now,
    )
    session.add(check)

    monitor.last_status = outcome.status
    monitor.last_checked_at = now
    monitor.next_check_at = now + timedelta(seconds=monitor.interval_seconds)
    if outcome.body_hash is not None:
        monitor.last_body_hash = outcome.body_hash
    session.add(monitor)

    _update_incidents(session, monitor, outcome, now)

    session.commit()
    session.refresh(check)
    return check


def _update_incidents(session: Session, monitor: Monitor, outcome: CheckOutcome,
                      now: datetime) -> None:
    open_incident = _open_incident(session, monitor)
    reachable = outcome.status in (CheckStatus.UP, CheckStatus.CHANGED)

    if not reachable and open_incident is None:
        detail = outcome.error or "down"
        session.add(Incident(monitor_id=monitor.id, status=CheckStatus.DOWN,
                             detail=detail, started_at=now))
        notify.send_incident(monitor, opened=True, detail=detail)
    elif reachable and open_incident is not None:
        open_incident.resolved_at = now
        session.add(open_incident)
        notify.send_incident(monitor, opened=False, detail="back up")


def _open_incident(session: Session, monitor: Monitor) -> Incident | None:
    from sqlmodel import select

    stmt = (select(Incident)
            .where(Incident.monitor_id == monitor.id, Incident.resolved_at.is_(None))
            .order_by(Incident.started_at.desc()))
    return session.exec(stmt).first()


def run_check(session: Session, monitor: Monitor, *, client: ApiClient,
              now: datetime | None = None) -> Check:
    """Full pipeline: perform the check, then record it."""
    outcome = perform_check(monitor, client)
    return record_check(session, monitor, outcome, now=now)
