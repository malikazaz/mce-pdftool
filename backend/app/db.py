"""SQLite persistence for project records.

We use the stdlib ``sqlite3`` module directly (no ORM) to keep the dependency
surface small. Only project *metadata* is stored here — never document contents.
Page classifications travel inside the generate payload and are held in frontend
state; persisting them is a documented future extension.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from .config import get_settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id           TEXT PRIMARY KEY,
    original_pdf_path    TEXT,
    translated_pdf_path  TEXT,
    original_page_count  INTEGER,
    translated_page_count INTEGER,
    created_at           TEXT NOT NULL,
    output_dir           TEXT NOT NULL,
    status               TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_project(project_id: str, output_dir: str) -> dict[str, Any]:
    created_at = utcnow_iso()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO projects (project_id, created_at, output_dir, status)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, created_at, output_dir, "created"),
        )
    return get_project(project_id)  # type: ignore[return-value]


def get_project(project_id: str) -> Optional[dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE project_id = ?", (project_id,)
        ).fetchone()
    return dict(row) if row else None


def update_project(project_id: str, **fields: Any) -> None:
    if not fields:
        return
    allowed = {
        "original_pdf_path",
        "translated_pdf_path",
        "original_page_count",
        "translated_page_count",
        "status",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    assignments = ", ".join(f"{k} = ?" for k in updates)
    with _connect() as conn:
        conn.execute(
            f"UPDATE projects SET {assignments} WHERE project_id = ?",
            (*updates.values(), project_id),
        )


def delete_project(project_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))


def list_projects_older_than(hours: int) -> list[dict[str, Any]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM projects WHERE created_at < ?", (cutoff,)
        ).fetchall()
    return [dict(r) for r in rows]
