"""The scheduler: find monitors whose next check is due and enqueue them.

It does not run checks itself — it only dispatches jobs onto the taskq queue,
bumping each monitor's ``next_check_at`` immediately so a slow check can't be
enqueued twice. A taskq worker does the actual work.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

from sqlmodel import Session, select

from .config import get_settings
from .db import engine
from .models import Monitor, utcnow


def enqueue_due(session: Session, queue, *, now: datetime | None = None) -> int:
    """Enqueue a check for every due, unpaused monitor. Returns how many."""
    now = now or utcnow()
    due = session.exec(
        select(Monitor).where(Monitor.paused == False, Monitor.next_check_at <= now)  # noqa: E712
    ).all()
    for monitor in due:
        queue.enqueue("check_monitor", args=[monitor.id], max_retries=1)
        # Claim it so the next scheduler tick won't re-enqueue before the check
        # finishes; the check itself will set a precise next_check_at.
        monitor.next_check_at = now + timedelta(seconds=monitor.interval_seconds)
        session.add(monitor)
    session.commit()
    return len(due)


def run_scheduler(*, stop: threading.Event | None = None, on_tick=None) -> None:
    """Loop forever, enqueuing due checks every ``scheduler_interval`` seconds."""
    from .tasks import queue

    settings = get_settings()
    stop = stop or threading.Event()
    while not stop.wait(settings.scheduler_interval):
        with Session(engine) as session:
            count = enqueue_due(session, queue)
        if on_tick:
            on_tick(count)
