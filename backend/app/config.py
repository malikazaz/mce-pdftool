"""Application configuration.

All settings are environment-overridable (prefix ``MCE_``) so the tool can be
reconfigured when embedded in the MedConnect portal without code changes.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Default data directory lives next to the backend package: backend/data
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DATA_DIR = _BACKEND_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCE_", env_file=".env", extra="ignore")

    # Where all temporary project data and the SQLite db live.
    data_dir: Path = _DEFAULT_DATA_DIR

    # Reject uploads larger than this (per file). Sensible cap for scanned PDFs.
    max_upload_mb: int = 50

    # Projects (and their files) older than this are removed by the cleanup task.
    cleanup_age_hours: int = 24

    # How often the background cleanup task runs.
    cleanup_interval_minutes: int = 60

    # Width (px) of rendered page thumbnails. Height scales to preserve aspect.
    thumbnail_width: int = 240

    # CORS origins allowed to call the API (the Vite dev server by default).
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"


@lru_cache
def get_settings() -> Settings:
    return Settings()
