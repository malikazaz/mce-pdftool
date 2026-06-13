"""Automatic removal of stale projects (folders + db rows).

Sensitive student documents must not linger. ``cleanup_old_projects`` is run on
startup and on a periodic background task; it is also importable so it could be
wired to an external cron/scheduler if the portal prefers that.
"""

from __future__ import annotations

import asyncio
import logging

from . import db, storage_service
from .config import get_settings

logger = logging.getLogger("mce.cleanup")


def cleanup_old_projects() -> int:
    """Delete every project older than the configured age. Returns count removed."""
    settings = get_settings()
    stale = db.list_projects_older_than(settings.cleanup_age_hours)
    for project in stale:
        project_id = project["project_id"]
        storage_service.remove_project_dir(project_id)
        db.delete_project(project_id)
    if stale:
        # Log the count only — never project ids or filenames.
        logger.info("Cleanup removed %d stale project(s).", len(stale))
    return len(stale)


async def cleanup_loop() -> None:
    """Background task: run cleanup forever at the configured interval."""
    settings = get_settings()
    interval_seconds = max(60, settings.cleanup_interval_minutes * 60)
    while True:
        try:
            cleanup_old_projects()
        except Exception:  # never let the loop die on a transient error
            logger.exception("Cleanup pass failed.")
        await asyncio.sleep(interval_seconds)
