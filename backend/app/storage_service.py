"""Filesystem helpers: project folders, filename sanitisation, path-traversal guard.

Every filesystem path that incorporates user-supplied input MUST be built via
``safe_join`` / ``sanitise_filename`` so a malicious project id or filename can
never escape the data directory.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .config import get_settings

# Characters that are unsafe in a filename across platforms, plus control chars.
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_join(base: Path, *parts: str) -> Path:
    """Join ``parts`` onto ``base`` and guarantee the result stays inside ``base``.

    Raises ``ValueError`` on any attempt to traverse outside (e.g. ``..``).
    """
    base_resolved = base.resolve()
    candidate = base_resolved.joinpath(*parts).resolve()
    if base_resolved != candidate and base_resolved not in candidate.parents:
        raise ValueError("Resolved path escapes the permitted base directory")
    return candidate


def sanitise_filename(name: str, *, default_stem: str = "document") -> str:
    """Return a safe ``*.pdf`` basename derived from ``name``.

    Strips directory separators, ``..``, and control characters. Always forces a
    single ``.pdf`` extension. Falls back to ``default_stem`` if nothing usable
    remains.
    """
    # Keep only the basename — discard any path components an attacker injected.
    base = Path(name.strip()).name
    base = _UNSAFE_CHARS.sub("_", base)
    base = base.replace("..", "_").strip(" .")

    stem = base[:-4] if base.lower().endswith(".pdf") else base
    stem = stem.strip(" ._") or default_stem
    return f"{stem}.pdf"


def project_dir(project_id: str) -> Path:
    """Return the (validated) directory for a project."""
    return safe_join(get_settings().projects_dir, project_id)


def ensure_project_dirs(project_id: str) -> Path:
    """Create the project's folder tree and return its root."""
    root = project_dir(project_id)
    (root / "outputs").mkdir(parents=True, exist_ok=True)
    return root


def remove_project_dir(project_id: str) -> None:
    """Delete a project's folder tree if it exists (best effort)."""
    root = project_dir(project_id)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
