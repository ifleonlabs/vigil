# vigil

An **uptime & change monitoring service**: register URLs to watch, and vigil checks them on a schedule — recording status, latency, and uptime, opening incidents when something goes down, and flagging when a page's content changes.

This is **project #12** in a progressive Python series, and the first **top-of-the-pyramid** application: it's assembled from the reusable *engine parts* built earlier in the series, pulled straight from GitHub as dependencies —

- **[apikit](https://github.com/ifleonlabs/apikit)** runs every check (HTTP GET with timeout + retry/backoff)
- **[taskq](https://github.com/ifleonlabs/taskq)** runs checks as durable background jobs

plus FastAPI, SQLModel/SQLite, and JWT auth (the `auth-api` pattern). The point of vigil is to prove the ecosystem composes — the small libraries snap together into a real product.

```toml
# pyproject.toml — the bottom of the pyramid, installed into the top
[tool.uv.sources]
apikit = { git = "https://github.com/ifleonlabs/apikit" }
taskq  = { git = "https://github.com/ifleonlabs/taskq" }
```

## What it does

- **Monitors** — watch a URL on an interval; assert an expected status code, optionally require a keyword in the body, optionally watch for content changes
- **Checks** — each run records `up` / `down` / `changed`, the HTTP status, and latency
- **Incidents** — opened automatically when a monitor goes down, resolved when it recovers
- **Stats** — uptime ratio and average latency over a recent window
- **Multi-user** — JWT auth; each user owns their own monitors
- **Dashboard** — a clean web UI to add monitors and watch their status

## Install & run

```bash
git clone https://github.com/ifleonlabs/vigil.git
cd vigil
uv sync                       # also fetches apikit + taskq from GitHub

uv run vigil run              # web + scheduler + worker in one process
# open http://127.0.0.1:8000, register, and add a monitor
```

For production you'd typically run the pieces separately:

```bash
uv run vigil serve            # the API + dashboard
uv run vigil scheduler        # enqueues due checks
uv run vigil worker           # taskq worker that executes checks
uv run vigil create-user alice
```

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
uv run pytest        # 19 tests, fully offline
```

Every HTTP check in the tests is served by `httpx.MockTransport` through apikit, so the suite never touches the network — including the check engine, incident logic, scheduler dispatch, auth, and the full API via FastAPI's `TestClient`.

## Project layout

```
vigil/
├── pyproject.toml          # depends on apikit + taskq from GitHub
├── main.py
├── src/vigil/
│   ├── config.py           # settings (.env)
│   ├── db.py               # SQLite engine/session
│   ├── models.py           # User / Monitor / Check / Incident
│   ├── security.py         # bcrypt + JWT
│   ├── checks.py           # the apikit-powered check engine
│   ├── stats.py            # uptime / latency / incident summaries
│   ├── scheduler.py        # enqueue due checks
│   ├── tasks.py            # taskq check job
│   ├── app.py              # FastAPI app
│   ├── cli.py              # serve / worker / scheduler / create-user
│   └── templates/dashboard.html
└── tests/
```

## License

MIT
