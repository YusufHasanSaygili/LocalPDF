from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "LocalPDF"
    app_version: str = "0.2.0"
    database_url: str = "postgresql+psycopg://localpdf:localpdf-local-only@localhost:5432/localpdf"
    local_data_dir: Path = Path("./data")
    max_upload_bytes: int = 524_288_000
    max_pdf_pages: int = 2_000
    job_lease_seconds: int = 120
    job_max_attempts: int = 3
    tool_timeout_seconds: int = 600
    preview_dpi: int = 110
    invite_token_pepper: str = "local-first-demo-pepper-change-in-dot-env"
    smtp_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_starttls: bool = True
    default_expiry_days: int | None = None
    expired_purge_grace_days: int = 7
    log_level: str = "INFO"
    telemetry_enabled: bool = Field(default=False)

    @property
    def store_root(self) -> Path:
        return self.local_data_dir.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
