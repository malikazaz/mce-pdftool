"""Bundle generated output PDFs into a single ZIP using the stdlib only."""

from __future__ import annotations

import zipfile
from pathlib import Path


def build_zip(output_paths: list[str | Path], dest_zip: str | Path) -> Path:
    """Write each file in ``output_paths`` into ``dest_zip`` under its basename."""
    dest = Path(dest_zip)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in output_paths:
            path = Path(p)
            zf.write(path, arcname=path.name)
    return dest
