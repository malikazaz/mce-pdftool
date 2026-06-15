"""Local text extraction for page classification.

Two-stage, fully offline:
1. Read the PDF's embedded text layer via PyMuPDF (instant, free, accurate) — works for
   digital PDFs.
2. If a page has little/no embedded text (a scan), render it to an image and OCR it with
   Tesseract via ``pytesseract``.

Everything runs on this server. Extracted text is returned to the caller for in-memory
classification only — it is **never logged or written to disk** (sensitive student data).

If Tesseract is not installed, the OCR stage is skipped and scanned pages simply yield no
text; callers treat that as "no suggestion" so manual labelling still works.
"""

from __future__ import annotations

import functools
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from .config import get_settings


def _configure_tesseract() -> None:
    cmd = get_settings().tesseract_cmd
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


@functools.lru_cache(maxsize=1)
def tesseract_available() -> bool:
    """True if the Tesseract binary can be invoked."""
    _configure_tesseract()
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def languages_available() -> frozenset[str]:
    """Installed Tesseract language codes (empty set if Tesseract is unavailable)."""
    if not tesseract_available():
        return frozenset()
    try:
        return frozenset(pytesseract.get_languages(config=""))
    except Exception:
        return frozenset()


def _embedded_text(page: "fitz.Page") -> str:
    try:
        return page.get_text("text").strip()
    except Exception:
        return ""


def _ocr_page(page: "fitz.Page", lang: str) -> str:
    """Render the page to an image and OCR it. Returns "" if OCR is unavailable."""
    if not tesseract_available():
        return ""
    # Fall back to English if the requested language pack isn't installed.
    langs = languages_available()
    use_lang = lang if lang in langs else ("eng" if "eng" in langs else None)
    if use_lang is None:
        return ""
    try:
        dpi = get_settings().ocr_dpi
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return pytesseract.image_to_string(img, lang=use_lang).strip()
    except Exception:
        return ""


def extract_page_text(pdf_path: str | Path, page_1based: int, lang: str = "eng") -> str:
    """Return the text of one page: embedded layer first, OCR fallback for scans."""
    doc = fitz.open(str(pdf_path))
    try:
        page = doc.load_page(page_1based - 1)
        text = _embedded_text(page)
        if len(text) >= get_settings().ocr_text_threshold:
            return text
        ocr_text = _ocr_page(page, lang)
        # Prefer whichever produced more usable text.
        return ocr_text if len(ocr_text) > len(text) else text
    finally:
        doc.close()
