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

    # --- Auto-classification (local OCR) ---
    # Optional explicit path to the Tesseract binary (e.g. on Windows:
    # "C:/Program Files/Tesseract-OCR/tesseract.exe"). Empty = rely on PATH.
    tesseract_cmd: str = ""
    # DPI used when rendering a page to an image for OCR. Higher = slower, more accurate.
    # 300 reads faint/low-contrast certificate scans far better than 200, at a modest cost.
    ocr_dpi: int = 300
    # Below this many extracted characters a page is treated as "needs OCR".
    ocr_text_threshold: int = 20
    # Parallel OCR workers for page classification. 0 = auto (min(8, CPU count)). Each worker
    # runs a separate Tesseract process, so this scales nearly linearly with cores. Lower it
    # on memory-constrained hosts (e.g. 1–2); raise it on a beefy server.
    ocr_workers: int = 0

    # CORS origins allowed to call the API (the Vite dev server by default).
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Directory of the built frontend (Vite `dist`). When set and present, the API also
    # serves the SPA from the same origin — the single-service production deploy. Empty in
    # dev/tests, where the Vite dev server handles the UI.
    static_dir: str = ""

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
