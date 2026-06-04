"""Application settings, loaded from the environment / a .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

# The insecure default — must be overridden in production (see Settings.check_security).
DEFAULT_SECRET = "dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIGIL_", env_file=".env", extra="ignore")

    # Environment
    env: str = "development"             # set VIGIL_ENV=production to harden

    # Storage
    database_url: str = "sqlite:///vigil.db"
    queue_path: str = "vigil-queue.db"

    # Auth
    secret_key: str = DEFAULT_SECRET
    access_token_minutes: int = 60 * 24
    auth_max_attempts: int = 20          # per-IP login/register attempts per window
    auth_window_seconds: float = 60.0

    # Checking behavior
    check_timeout: float = 10.0          # seconds per HTTP check
    check_retries: int = 1               # apikit retries on a transient failure
    scheduler_interval: float = 5.0      # how often the scheduler scans for due checks
    default_interval_seconds: int = 300  # default monitor poll interval

    @property
    def access_token_seconds(self) -> int:
        return self.access_token_minutes * 60

    @property
    def is_production(self) -> bool:
        return self.env.lower() in ("production", "prod")

    def check_security(self) -> None:
        """Fail fast in production if the secret key is missing/weak."""
        if self.is_production and (
            self.secret_key in (DEFAULT_SECRET, "") or len(self.secret_key) < 16
        ):
            raise RuntimeError(
                "VIGIL_SECRET_KEY is missing or too weak for production. "
                "Set a strong secret, e.g. "
                "VIGIL_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
            )


def get_settings() -> Settings:
    return Settings()
