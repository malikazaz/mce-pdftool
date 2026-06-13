"""FastAPI application entrypoint.

Privacy note: request logging is restricted to method/path/status. We never log
filenames, project ids, or any document contents/extracted text — these are
sensitive student documents.

PORTAL-AUTH: To integrate with the MedConnect portal, mount this app behind the
portal's auth middleware (or add a router dependency in routes/projects.py) and
tighten ``allowed_origins`` to the portal origin.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .cleanup import cleanup_loop, cleanup_old_projects
from .config import get_settings
from .routes import projects

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mce")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    cleanup_old_projects()  # immediate sweep on boot
    task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="MedConnect Europe — PDF Assembly Tool", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(projects.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
