"""Database models for vigil.

NOTE: this module deliberately does NOT use ``from __future__ import annotations``.
SQLModel resolves ``Relationship`` fields from real (non-stringized) annotations,
and the future import breaks that — a gotcha learned earlier in this series.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    # Naive UTC: SQLite/SQLModel does not preserve tzinfo on read, so keeping
    # everything naive avoids "can't compare offset-naive and offset-aware"
    # errors and keeps stored timestamps lexicographically comparable.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CheckStatus(str, Enum):
    UP = "up"          # reachable and matched expectations
    DOWN = "down"      # unreachable, timed out, or wrong status
    CHANGED = "changed"  # reachable but the watched content changed


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=utcnow)

    monitors: list["Monitor"] = Relationship(back_populates="owner")


class Monitor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    name: str
    url: str
    interval_seconds: int = 300
    expected_status: int = 200
    keyword: Optional[str] = None        # if set, body must contain it (else DOWN)
    watch_content: bool = False          # if true, body-hash changes -> CHANGED
    paused: bool = False
    webhook_url: Optional[str] = None    # if set, incidents POST here (via notifykit)

    # Rolling state, updated by each check.
    last_status: Optional[CheckStatus] = None
    last_checked_at: Optional[datetime] = None
    next_check_at: datetime = Field(default_factory=utcnow, index=True)
    last_body_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    owner: Optional[User] = Relationship(back_populates="monitors")
    checks: list["Check"] = Relationship(
        back_populates="monitor",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    incidents: list["Incident"] = Relationship(
        back_populates="monitor",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Check(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    monitor_id: int = Field(foreign_key="monitor.id", index=True)
    status: CheckStatus
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    checked_at: datetime = Field(default_factory=utcnow, index=True)

    monitor: Optional[Monitor] = Relationship(back_populates="checks")


class Incident(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    monitor_id: int = Field(foreign_key="monitor.id", index=True)
    status: CheckStatus               # the bad state that opened the incident
    detail: str = ""
    started_at: datetime = Field(default_factory=utcnow)
    resolved_at: Optional[datetime] = None

    monitor: Optional[Monitor] = Relationship(back_populates="incidents")

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None
