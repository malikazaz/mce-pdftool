"""Test fixtures: deterministic sample PDFs whose pages carry an identifiable
label so page ORDER can be asserted exactly after assembly.

Each page is stamped with a unique marker string (e.g. "ORIG-P3"). We read it
back from generated PDFs via pypdf's text extraction to verify ordering.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def make_pdf(path: Path, markers: list[str]) -> None:
    """Create a PDF with one page per marker; each page prints its marker text."""
    c = canvas.Canvas(str(path), pagesize=A4)
    for marker in markers:
        c.setFont("Helvetica", 40)
        c.drawString(72, 700, marker)
        c.showPage()
    c.save()


def page_marker(reader: PdfReader, index_0based: int) -> str:
    """Return the (stripped) text of a page, used to identify which page it is."""
    return reader.pages[index_0based].extract_text().strip()


@pytest.fixture
def sample_pdfs(tmp_path: Path) -> dict[str, Path]:
    """A realistic pair.

    Original (5 pages): solicitor, apostille, academic, other, academic
    Translated (6 pages): solicitor, apostille, academic, other, academic, notary
    """
    original = tmp_path / "original.pdf"
    translated = tmp_path / "translated.pdf"
    make_pdf(
        original,
        ["ORIG-SOL", "ORIG-APO", "ORIG-ACAD1", "ORIG-OTHER1", "ORIG-ACAD2"],
    )
    make_pdf(
        translated,
        ["TR-SOL", "TR-APO", "TR-ACAD1", "TR-OTHER1", "TR-ACAD2", "TR-NOTARY"],
    )
    return {"original": original, "translated": translated}


@pytest.fixture
def isolated_data_dir(tmp_path: Path, monkeypatch):
    """Point the app's settings at a throwaway data dir and reset the cache."""
    from app import config

    data_dir = tmp_path / "data"
    monkeypatch.setenv("MCE_DATA_DIR", str(data_dir))
    config.get_settings.cache_clear()
    yield data_dir
    config.get_settings.cache_clear()
