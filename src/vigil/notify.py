"""Incident alerting, powered by the notifykit engine part.

When a monitor has a ``webhook_url``, opening or resolving an incident POSTs a
notification to it. Delivery is best-effort — notifykit's Notifier never raises,
so a flaky webhook can't disrupt the check pipeline.
"""

from __future__ import annotations

from notifykit import Level, Notifier, WebhookChannel

from .models import Monitor


def build_notifier(webhook_url: str) -> Notifier:
    """Create a Notifier for a monitor's webhook. Patch this in tests."""
    return Notifier(WebhookChannel(webhook_url))


def send_incident(monitor: Monitor, *, opened: bool, detail: str) -> None:
    """Alert that a monitor's incident just opened (down) or resolved (recovered)."""
    if not monitor.webhook_url:
        return
    notifier = build_notifier(monitor.webhook_url)
    level = Level.ERROR if opened else Level.SUCCESS
    headline = "DOWN" if opened else "RECOVERED"
    notifier.send(
        f"{headline}: {monitor.name}",
        body=detail,
        level=level,
        fields={"url": monitor.url, "monitor_id": monitor.id},
        source="vigil",
    )
