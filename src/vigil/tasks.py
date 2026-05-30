"""taskq integration: each monitor check is a durable background job.

The scheduler enqueues ``check_monitor`` jobs; a ``taskq`` worker claims and
runs them (with retries/backoff handled by taskq). The job is deliberately thin
— it just loads the monitor and delegates to the check engine.
"""

from __future__ import annotations

from sqlmodel import Session
from taskq import TaskQueue

from .checks import build_client, run_check
from .config import get_settings
from .db import engine
from .models import Monitor

queue = TaskQueue(get_settings().queue_path)


@queue.task(name="check_monitor", max_retries=1)
def check_monitor(monitor_id: int) -> str:
    """Run a single monitor's check. Registered as a taskq task."""
    with Session(engine) as session:
        monitor = session.get(Monitor, monitor_id)
        if monitor is None or monitor.paused:
            return "skipped"
        client = build_client()
        try:
            check = run_check(session, monitor, client=client)
        finally:
            client.close()
        return check.status.value
