# ── Stage 1: build the React frontend ───────────────────────────────────
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: the Python API (serves the built frontend) ──────────────────
FROM python:3.12-slim
# git: fetch the engine-part deps (apikit/taskq/notifykit) pinned in uv.lock.
# curl: container healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first (cached unless pyproject/lock change).
# README.md is required because pyproject declares it as the project readme.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Bring in the built SPA so FastAPI serves it at /.
COPY --from=frontend /frontend/dist ./frontend/dist

ENV PATH="/app/.venv/bin:$PATH" VIGIL_ENV=production
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "vigil.app:app", "--host", "0.0.0.0", "--port", "8000"]
