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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# reportlab's built-in Helvetica is Latin-1 only and cannot embed Cyrillic. Register a
# Unicode TTF so Bulgarian test text survives into the PDF text layer (needed for the
# direct Bulgarian classification tests). Falls back to Helvetica if none is found.
_UNICODE_FONT = "Helvetica"
for _candidate in (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
):
    if os.path.exists(_candidate):
        try:
            pdfmetrics.registerFont(TTFont("UnicodeTest", _candidate))
            _UNICODE_FONT = "UnicodeTest"
            break
        except Exception:
            pass


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


def make_text_pdf(path: Path, pages: list[str]) -> None:
    """Create a PDF with one page per string, embedding that string as real text.

    Wraps long text across lines so the classifier's embedded-text path sees full content
    (no OCR required in tests)."""
    c = canvas.Canvas(str(path), pagesize=A4)
    for body in pages:
        c.setFont(_UNICODE_FONT, 12)
        y = 760
        for line in body.split("\n"):
            words, current = line.split(" "), ""
            for w in words:
                if len(current) + len(w) > 90:
                    c.drawString(60, y, current)
                    y -= 16
                    current = w
                else:
                    current = f"{current} {w}".strip()
            c.drawString(60, y, current)
            y -= 16
        c.showPage()
    c.save()


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
