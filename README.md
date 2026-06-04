# vigil

An **uptime & change monitoring service**: register URLs to watch, and vigil checks them on a schedule — recording status, latency, and uptime, opening incidents when something goes down, and flagging when a page's content changes.

This is **project #12** in a progressive Python series, and the first **top-of-the-pyramid** application: it's assembled from the reusable *engine parts* built earlier in the series, pulled straight from GitHub as dependencies —

- **[apikit](https://github.com/ifleonlabs/apikit)** runs every check (HTTP GET with timeout + retry/backoff)
- **[taskq](https://github.com/ifleonlabs/taskq)** runs checks as durable background jobs
- **[notifykit](https://github.com/ifleonlabs/notifykit)** sends incident alerts to a webhook (and itself rides on apikit)

plus FastAPI, SQLModel/SQLite, and JWT auth (the `auth-api` pattern). The point of vigil is to prove the ecosystem composes — the small libraries snap together into a real product.

```toml
# pyproject.toml — the bottom of the pyramid, installed into the top
[tool.uv.sources]
apikit    = { git = "https://github.com/ifleonlabs/apikit" }
taskq     = { git = "https://github.com/ifleonlabs/taskq" }
notifykit = { git = "https://github.com/ifleonlabs/notifykit" }
```

## What it does

- **Monitors** — watch a URL on an interval; assert an expected status code, optionally require a keyword in the body, optionally watch for content changes
- **Checks** — each run records `up` / `down` / `changed`, the HTTP status, and latency
- **Incidents** — opened automatically when a monitor goes down, resolved when it recovers
- **Alerts** — give a monitor a `webhook_url` and incident open/resolve POSTs a notification there (via notifykit; best-effort, never blocks a check)
- **Stats** — uptime ratio and average latency over a recent window
- **Multi-user** — JWT auth; each user owns their own monitors
- **Dashboard** — a polished OLED-dark operations UI: live status badges, uptime/latency tiles, auto-refresh, skeleton loaders, toasts, inline-validated forms, and keyboard/screen-reader accessibility. The visual language is documented in [DESIGN.md](DESIGN.md) and shared across the ifleonlabs apps.

## Frontend + backend

vigil is split into a **Python API** (FastAPI) and a **React frontend** (Vite + TypeScript) in [`frontend/`](frontend/). In dev they run side by side and Vite proxies `/api` to the backend (no CORS). In prod the frontend builds to `frontend/dist` and FastAPI serves it.

### Run it (development) — one command

```bash
git clone https://github.com/ifleonlabs/vigil.git
cd vigil
uv sync                       # fetches apikit + taskq + notifykit from GitHub
python dev.py                 # starts the API AND the React dev server together
# open http://127.0.0.1:5173  (first run installs the frontend deps automatically)
```

`dev.py` runs `uv run vigil serve` (API on :8000) and `npm run dev` (frontend on :5173) in one process; Ctrl+C stops both.

> Want checks to run on a schedule while developing? Also start `uv run vigil scheduler` and `uv run vigil worker`. The frontend's **Check now** button works without them.

### Run it (production)

```bash
cd frontend && npm install && npm run build && cd ..   # build the SPA -> frontend/dist
uv run vigil serve            # FastAPI now serves the built app at http://127.0.0.1:8000
uv run vigil scheduler        # enqueues due checks
uv run vigil worker           # taskq worker that executes checks
uv run vigil create-user alice
```

No build step? `uv run vigil serve` falls back to a self-contained HTML dashboard when `frontend/dist` is absent.

### Run it (Docker)

```bash
VIGIL_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))") \
  docker compose up --build
# → http://localhost:8000  (web + scheduler + worker, with a healthcheck)
```

The image is a multi-stage build (builds the React frontend, then runs the API serving it) and runs with `VIGIL_ENV=production`, so it **refuses to start without a real `VIGIL_SECRET_KEY`**. See [`.env.example`](.env.example) for all settings and [`SECURITY.md`](SECURITY.md) for the security posture (headers, auth rate limiting, scanning).

## Architecture

```
                 ┌── scheduler ──┐ enqueues due checks
   Monitors ─────┤               ├──────────────▶ taskq queue (SQLite)
   (SQLite)      └───────────────┘                      │
                                                        ▼
   Dashboard ◀── FastAPI API ──▶ DB ◀── check engine ── taskq worker
   (web UI)        (JWT auth)            (apikit GET)
```

- **`checks.py`** — the heart: `perform_check` fetches a monitor's URL with apikit and classifies the result; `record_check` persists it and manages incidents.
- **`scheduler.py`** — finds monitors whose `next_check_at` has passed and enqueues a `check_monitor` job, reclaiming each so it can't be double-dispatched.
- **`tasks.py`** — the `check_monitor` taskq task that a worker runs.
- **`app.py`** — FastAPI: register/login, monitor CRUD, an immediate `/check` endpoint, and the dashboard.

## How checks are classified

| Result | When |
|---|---|
| **up** | reachable, status matches, keyword present (if set) |
| **down** | unreachable/timeout, wrong status, or keyword missing |
| **changed** | reachable, but the watched body hash differs from last time |

Down results open an incident (resolved on the next reachable check). apikit gives each check a timeout and a retry on transient failures for free.

## Development

```bash
uv sync
uv run pytest        # 21 tests, fully offline
```

Every HTTP check in the tests is served by `httpx.MockTransport` through apikit, so the suite never touches the network — including the check engine, incident logic, scheduler dispatch, auth, and the full API via FastAPI's `TestClient`.

## Project layout

```
vigil/
├── pyproject.toml          # depends on apikit + taskq + notifykit from GitHub
├── dev.py                  # run the API + React frontend together
├── main.py
├── DESIGN.md               # the shared ifleon design system
├── src/vigil/
│   ├── config.py           # settings (.env)
│   ├── db.py               # SQLite engine/session
│   ├── models.py           # User / Monitor / Check / Incident
│   ├── security.py         # bcrypt + JWT
│   ├── checks.py           # the apikit-powered check engine
│   ├── stats.py            # uptime / latency / incident summaries
│   ├── scheduler.py        # enqueue due checks
│   ├── tasks.py            # taskq check job
│   ├── notify.py           # incident alerts via notifykit
│   ├── app.py              # FastAPI app (API + serves the built frontend)
│   ├── cli.py              # serve / worker / scheduler / create-user
│   └── templates/dashboard.html   # no-build fallback UI
├── frontend/               # Vite + React + TypeScript dashboard
│   └── src/                # api.ts, App.tsx, components/, index.css (design system)
└── tests/
```

## License

MIT
