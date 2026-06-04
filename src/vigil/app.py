"""The FastAPI application: auth, monitor CRUD, and dashboard endpoints."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from . import security, stats
from .checks import build_client, run_check
from .db import get_session, init_db
from .models import Monitor, User, utcnow
from .schemas import (
    CheckOut,
    Credentials,
    MonitorCreate,
    MonitorDetail,
    MonitorOut,
    MonitorUpdate,
    Token,
)

# The React frontend builds to vigil/frontend/dist. When present we serve it;
# otherwise we fall back to the self-contained legacy template (no build needed).
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_DASHBOARD_HTML = (Path(__file__).parent / "templates" / "dashboard.html").read_text(
    encoding="utf-8"
)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="vigil", description="Uptime & change monitoring.", lifespan=lifespan)
_bearer = HTTPBearer(auto_error=False)


# --- auth ----------------------------------------------------------------
def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    username = security.decode_token(creds.credentials)
    if username is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user


@app.post("/api/register", response_model=Token)
def register(body: Credentials, session: Session = Depends(get_session)) -> Token:
    if session.exec(select(User).where(User.username == body.username)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    user = User(username=body.username, password_hash=security.hash_password(body.password))
    session.add(user)
    session.commit()
    return Token(access_token=security.create_access_token(user.username), username=user.username)


@app.post("/api/login", response_model=Token)
def login(body: Credentials, session: Session = Depends(get_session)) -> Token:
    user = session.exec(select(User).where(User.username == body.username)).first()
    if user is None or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad username or password")
    return Token(access_token=security.create_access_token(user.username), username=user.username)


# --- monitors ------------------------------------------------------------
def _get_owned(session: Session, monitor_id: int, user: User) -> Monitor:
    monitor = session.get(Monitor, monitor_id)
    if monitor is None or monitor.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Monitor not found")
    return monitor


def _to_out(session: Session, monitor: Monitor) -> MonitorOut:
    summary = stats.summarize(session, monitor)
    return MonitorOut(
        id=monitor.id, name=monitor.name, url=monitor.url,
        interval_seconds=monitor.interval_seconds, expected_status=monitor.expected_status,
        keyword=monitor.keyword, watch_content=monitor.watch_content, paused=monitor.paused,
        webhook_url=monitor.webhook_url,
        last_status=monitor.last_status, last_checked_at=monitor.last_checked_at,
        **summary,
    )


@app.get("/api/monitors", response_model=list[MonitorOut])
def list_monitors(user: User = Depends(current_user),
                  session: Session = Depends(get_session)) -> list[MonitorOut]:
    monitors = session.exec(
        select(Monitor).where(Monitor.owner_id == user.id).order_by(Monitor.created_at)
    ).all()
    return [_to_out(session, m) for m in monitors]


@app.post("/api/monitors", response_model=MonitorOut, status_code=201)
def create_monitor(body: MonitorCreate, user: User = Depends(current_user),
                   session: Session = Depends(get_session)) -> MonitorOut:
    monitor = Monitor(owner_id=user.id, next_check_at=utcnow(), **body.model_dump())
    session.add(monitor)
    session.commit()
    session.refresh(monitor)
    return _to_out(session, monitor)


@app.get("/api/monitors/{monitor_id}", response_model=MonitorDetail)
def get_monitor(monitor_id: int, user: User = Depends(current_user),
                session: Session = Depends(get_session)) -> MonitorDetail:
    monitor = _get_owned(session, monitor_id, user)
    out = _to_out(session, monitor)
    checks = [CheckOut(**c.model_dump()) for c in stats.recent_checks(session, monitor.id)]
    return MonitorDetail(**out.model_dump(), recent_checks=checks)


@app.patch("/api/monitors/{monitor_id}", response_model=MonitorOut)
def update_monitor(monitor_id: int, body: MonitorUpdate, user: User = Depends(current_user),
                   session: Session = Depends(get_session)) -> MonitorOut:
    monitor = _get_owned(session, monitor_id, user)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(monitor, field, value)
    session.add(monitor)
    session.commit()
    session.refresh(monitor)
    return _to_out(session, monitor)


@app.delete("/api/monitors/{monitor_id}", status_code=204)
def delete_monitor(monitor_id: int, user: User = Depends(current_user),
                   session: Session = Depends(get_session)) -> None:
    monitor = _get_owned(session, monitor_id, user)
    session.delete(monitor)
    session.commit()


@app.post("/api/monitors/{monitor_id}/check", response_model=CheckOut)
def check_now(monitor_id: int, user: User = Depends(current_user),
              session: Session = Depends(get_session)) -> CheckOut:
    """Run a check immediately (synchronously) — handy for the UI and demos."""
    monitor = _get_owned(session, monitor_id, user)
    client = build_client()
    try:
        check = run_check(session, monitor, client=client)
    finally:
        client.close()
    return CheckOut(**check.model_dump())


# --- UI ------------------------------------------------------------------
# Serve the built React app when it exists; otherwise the legacy template.
# (Mounted last so it never shadows the /api routes declared above.)
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> HTMLResponse:
        return HTMLResponse(_DASHBOARD_HTML)
