"""Derived monitor statistics: uptime ratio, average latency, open incidents."""

from __future__ import annotations

from sqlalchemy import func
from sqlmodel import Session, select

from .models import Check, CheckStatus, Incident, Monitor

WINDOW = 50  # number of recent checks the summary is computed over


def recent_checks(session: Session, monitor_id: int, limit: int = WINDOW) -> list[Check]:
    stmt = (select(Check)
            .where(Check.monitor_id == monitor_id)
            .order_by(Check.checked_at.desc())
            .limit(limit))
    return list(session.exec(stmt))


def open_incident_count(session: Session, monitor_id: int) -> int:
    stmt = (select(func.count()).select_from(Incident)
            .where(Incident.monitor_id == monitor_id, Incident.resolved_at.is_(None)))
    return session.exec(stmt).one()


def summarize(session: Session, monitor: Monitor, window: int = WINDOW) -> dict:
    """Return uptime ratio + average latency over the recent window."""
    checks = recent_checks(session, monitor.id, window)
    if not checks:
        return {"uptime_ratio": None, "avg_latency_ms": None,
                "open_incidents": open_incident_count(session, monitor.id)}

    up = sum(1 for c in checks if c.status in (CheckStatus.UP, CheckStatus.CHANGED))
    latencies = [c.latency_ms for c in checks if c.latency_ms is not None]
    return {
        "uptime_ratio": up / len(checks),
        "avg_latency_ms": (sum(latencies) / len(latencies)) if latencies else None,
        "open_incidents": open_incident_count(session, monitor.id),
    }
