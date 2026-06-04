# Security

## Reporting a vulnerability

Please report security issues privately to the maintainer (open a [GitHub security advisory](https://github.com/ifleonlabs/vigil/security/advisories/new)) rather than a public issue. We aim to acknowledge within a few days.

## What's built in

- **Secret-key enforcement.** With `VIGIL_ENV=production`, the app refuses to boot while `VIGIL_SECRET_KEY` is the insecure default. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- **Password hashing.** bcrypt via the `bcrypt` library (passwords truncated to bcrypt's 72-byte limit).
- **JWT auth.** Short-lived HS256 access tokens; protected routes verify the token and the user on every request.
- **Auth rate limiting.** `/api/login` and `/api/register` are limited per client IP (`VIGIL_AUTH_MAX_ATTEMPTS` per `VIGIL_AUTH_WINDOW_SECONDS`) to blunt brute-force/credential-stuffing.
- **Security headers** on every response: `Content-Security-Policy` (self + Google Fonts only), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, and `Strict-Transport-Security`.
- **Per-user isolation.** Every monitor is owned by a user; cross-user access returns 404.
- **No secrets in the repo.** `.env` is gitignored; `.env.example` documents the variables.

## Automated scanning (CI)

On every push/PR, GitHub Actions runs:

- **pip-audit** — known CVEs in Python dependencies
- **bandit** — static analysis of the Python source
- **npm audit** — known CVEs in frontend dependencies
- **CodeQL** — semantic code scanning (Python + JavaScript/TypeScript)
- **Dependabot** — automated dependency-update PRs (pip, npm, GitHub Actions)

## Deployment notes

- Run behind a TLS-terminating reverse proxy (the HSTS header assumes HTTPS).
- The auth rate limiter is in-memory (per process). For multiple instances, put a shared limiter (e.g. Redis) in front, or rely on your proxy/WAF.
- The SQLite default is fine for a single instance; point `VIGIL_DATABASE_URL` at Postgres for multi-instance deployments.
- The no-build HTML fallback uses inline scripts and is **dev-only**; production serves the built React app, which is CSP-clean.
