"""Pydantic request/response shapes for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .models import CheckStatus


class Credentials(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class MonitorCreate(BaseModel):
    name: str
    url: str
    interval_seconds: int = 300
    expected_status: int = 200
    keyword: str | None = None
    watch_content: bool = False
    webhook_url: str | None = None


class MonitorUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    interval_seconds: int | None = None
    expected_status: int | None = None
    keyword: str | None = None
    watch_content: bool | None = None
    paused: bool | None = None
    webhook_url: str | None = None


class CheckOut(BaseModel):
    id: int
    status: CheckStatus
    status_code: int | None
    latency_ms: float | None
    error: str | None
    checked_at: datetime


class MonitorOut(BaseModel):
    id: int
    name: str
    url: str
    interval_seconds: int
    expected_status: int
    keyword: str | None
    watch_content: bool
    paused: bool
    webhook_url: str | None = None
    last_status: CheckStatus | None
    last_checked_at: datetime | None
    uptime_ratio: float | None = None     # over the recent window
    avg_latency_ms: float | None = None
    open_incidents: int = 0


class MonitorDetail(MonitorOut):
    recent_checks: list[CheckOut] = []
