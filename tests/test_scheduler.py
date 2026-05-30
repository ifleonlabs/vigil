"""Scheduler tests — which monitors get enqueued, using a fake queue."""

from __future__ import annotations

from datetime import timedelta

from vigil.models import Monitor, utcnow
from vigil.scheduler import enqueue_due


class FakeQueue:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, task_name, *, args=None, **kw):
        self.enqueued.append((task_name, args, kw))


def _add(session, owner_id, **kw):
    m = Monitor(owner_id=owner_id, name="m", url="https://x", **kw)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def test_only_due_unpaused_monitors_are_enqueued(session, user):
    now = utcnow()
    due = _add(session, user.id, next_check_at=now - timedelta(seconds=1), interval_seconds=60)
    _add(session, user.id, next_check_at=now + timedelta(seconds=60))      # not due
    _add(session, user.id, next_check_at=now - timedelta(seconds=1), paused=True)  # paused

    queue = FakeQueue()
    count = enqueue_due(session, queue, now=now)

    assert count == 1
    assert queue.enqueued == [("check_monitor", [due.id], {"max_retries": 1})]


def test_due_monitor_is_reclaimed_to_prevent_double_enqueue(session, user):
    now = utcnow()
    m = _add(session, user.id, next_check_at=now - timedelta(seconds=1), interval_seconds=120)

    queue = FakeQueue()
    enqueue_due(session, queue, now=now)
    session.refresh(m)
    # next_check_at pushed into the future, so a second tick won't re-enqueue it.
    assert m.next_check_at > now
    assert enqueue_due(session, queue, now=now) == 0
