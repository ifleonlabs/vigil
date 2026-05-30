"""Application settings, loaded from the environment / a .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIGIL_", env_file=".env", extra="ignore")

    # Storage
    database_url: str = "sqlite:///vigil.db"
    queue_path: str = "vigil-queue.db"

    # Auth
    secret_key: str = "dev-secret-change-me"
    access_token_minutes: int = 60 * 24

    # Checking behavior
    check_timeout: float = 10.0          # seconds per HTTP check
    check_retries: int = 1               # apikit retries on a transient failure
    scheduler_interval: float = 5.0      # how often the scheduler scans for due checks
    default_interval_seconds: int = 300  # default monitor poll interval

    @property
    def access_token_seconds(self) -> int:
        return self.access_token_minutes * 60


def get_settings() -> Settings:
    return Settings()
