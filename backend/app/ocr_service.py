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
import time
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageOps

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


# def _ocr_page(page: "fitz.Page", lang: str) -> str:
#     """Render the page to an image and OCR it. Returns "" if OCR is unavailable.
#
#     ``lang`` may be a Tesseract combo like "bul+eng"; unavailable packs are dropped and we
#     fall back to English so a missing Bulgarian pack never breaks classification.
#     """
#     if not tesseract_available():
#         return ""
#     langs = languages_available()
#     requested = [code for code in lang.split("+") if code in langs]
#     if not requested:
#         requested = ["eng"] if "eng" in langs else []
#     if not requested:
#         return ""
#     use_lang = "+".join(requested)
#     try:
#         dpi = get_settings().ocr_dpi
#         pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
#         img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
#         # Faint, low-contrast scans (e.g. certificates with a tinted background) OCR poorly
#         # in colour. Grayscale + autocontrast stretches the tonal range so light text on a
#         # tinted ground is legible to Tesseract — no thresholding (which can erase fine print).
#         img = ImageOps.autocontrast(img.convert("L"))
#         return pytesseract.image_to_string(img, lang=use_lang).strip()
#     except Exception:
#         return ""


# def _ocr_page(page: fitz.Page, lang: str) -> str:
#     if not tesseract_available():
#         return ""
#
#     langs = languages_available()
#     requested = [code for code in lang.split("+") if code in langs]
#     if not requested:
#         requested = ["eng"] if "eng" in langs else []
#     if not requested:
#         return ""
#
#     use_lang = "+".join(requested)
#
#     try:
#         start = time.perf_counter()
#
#         dpi = get_settings().ocr_dpi
#
#         render_start = time.perf_counter()
#         pix = page.get_pixmap(
#             matrix=fitz.Matrix(dpi / 72, dpi / 72)
#         )
#         print(
#             f"rendered size: {pix.width}x{pix.height}"
#         )
#         print(
#             f"render: {time.perf_counter() - render_start:.2f}s"
#         )
#
#         convert_start = time.perf_counter()
#         img = Image.frombytes(
#             "RGB",
#             (pix.width, pix.height),
#             pix.samples,
#         )
#         img = ImageOps.autocontrast(img.convert("L"))
#         print(
#             f"convert: {time.perf_counter() - convert_start:.2f}s"
#         )
#
#         ocr_start = time.perf_counter()
#         text = pytesseract.image_to_string(
#             img,
#             lang=use_lang,
#         )
#         print(
#             f"ocr ({use_lang}): "
#             f"{time.perf_counter() - ocr_start:.2f}s"
#         )
#
#         print(
#             f"total: {time.perf_counter() - start:.2f}s"
#         )
#
#         return text.strip()
#
#     except Exception as e:
#         print(f"OCR ERROR: {e}")
#         return ""


# def extract_page_text(pdf_path: str | Path, page_1based: int, lang: str = "eng") -> str:
#     """Return the text of one page: embedded layer first, OCR fallback for scans."""
#     start = time.perf_counter()
#     doc = fitz.open(str(pdf_path))
#     print(
#         f"open took "
#         f"{time.perf_counter() - start:.2f}s"
#     )
#     try:
#         page = doc.load_page(page_1based - 1)
#         text = _embedded_text(page)
#         if len(text) >= get_settings().ocr_text_threshold:
#             print(
#                 f"Page {page_1based}: embedded text "
#                 f"({len(text)} chars)"
#             )
#             return text
#         print(f"Page {page_1based}: OCR")
#         ocr_text = _ocr_page(page, lang)
#         # Prefer whichever produced more usable text.
#         return ocr_text if len(ocr_text) > len(text) else text
#     finally:
#         doc.close()

# def _ocr_page(page: "fitz.Page", lang: str) -> str:
#     if not tesseract_available():
#         return ""
#
#     langs = languages_available()
#
#     requested = [
#         code
#         for code in lang.split("+")
#         if code in langs
#     ]
#
#     if not requested:
#         requested = ["eng"] if "eng" in langs else []
#
#     if not requested:
#         return ""
#
#     use_lang = "+".join(requested)
#
#     try:
#         start = time.perf_counter()
#
#         dpi = get_settings().ocr_dpi
#
#         rect = page.rect
#
#         clip = fitz.Rect(
#             rect.x0,
#             rect.y0,
#             rect.x1,
#             rect.y1 * 0.30,
#         )
#
#         render_start = time.perf_counter()
#
#         pix = page.get_pixmap(
#             matrix=fitz.Matrix(dpi / 72, dpi / 72),
#             clip=clip,
#         )
#
#         print(
#             f"rendered size: {pix.width}x{pix.height}"
#         )
#
#         print(
#             f"render: "
#             f"{time.perf_counter() - render_start:.2f}s"
#         )
#
#         convert_start = time.perf_counter()
#
#         img = Image.frombytes(
#             "RGB",
#             (pix.width, pix.height),
#             pix.samples,
#         )
#
#         img = ImageOps.autocontrast(
#             img.convert("L")
#         )
#
#         print(
#             f"convert: "
#             f"{time.perf_counter() - convert_start:.2f}s"
#         )
#
#         ocr_start = time.perf_counter()
#
#         text = pytesseract.image_to_string(
#             img,
#             lang=use_lang,
#             config="--psm 6",
#         )
#
#         print(
#             f"ocr ({use_lang}): "
#             f"{time.perf_counter() - ocr_start:.2f}s"
#         )
#
#         print(
#             f"total: "
#             f"{time.perf_counter() - start:.2f}s"
#         )
#
#         return text.strip()
#
#     except Exception as e:
#         print(f"OCR ERROR: {e}")
#         return ""

def extract_page_text(
    pdf_path: str | Path,
    page_1based: int,
    lang: str = "eng",
) -> str:
    doc = fitz.open(str(pdf_path))

    try:
        page = doc.load_page(page_1based - 1)

        text = _embedded_text(page)

        if len(text) >= get_settings().ocr_text_threshold:
            return text

        return _ocr_page_fast(page, lang)

    finally:
        doc.close()


def _ocr_page_fast(page: fitz.Page, lang: str) -> str:
    if not tesseract_available():
        return ""

    langs = languages_available()

    requested = [
        code
        for code in lang.split("+")
        if code in langs
    ]

    if not requested:
        requested = ["eng"] if "eng" in langs else []

    if not requested:
        return ""

    use_lang = "+".join(requested)

    try:
        dpi = get_settings().ocr_dpi

        rect = page.rect

        clip = fitz.Rect(
            rect.x0,
            rect.y0,
            rect.x1,
            rect.y0 + (rect.height * 0.30),
        )

        pix = page.get_pixmap(
            matrix=fitz.Matrix(dpi / 72, dpi / 72),
            clip=clip,
        )

        img = Image.frombytes(
            "RGB",
            (pix.width, pix.height),
            pix.samples,
        )

        img = ImageOps.autocontrast(
            img.convert("L")
        )

        return pytesseract.image_to_string(
            img,
            lang=use_lang,
            config="--psm 6",
        ).strip()

    except Exception:
        return ""


def _ocr_page_full(page: fitz.Page, lang: str) -> str:
    if not tesseract_available():
        return ""

    langs = languages_available()

    requested = [
        code
        for code in lang.split("+")
        if code in langs
    ]

    if not requested:
        requested = ["eng"] if "eng" in langs else []

    if not requested:
        return ""

    use_lang = "+".join(requested)

    try:
        dpi = get_settings().ocr_dpi

        pix = page.get_pixmap(
            matrix=fitz.Matrix(dpi / 72, dpi / 72),
        )

        img = Image.frombytes(
            "RGB",
            (pix.width, pix.height),
            pix.samples,
        )

        img = ImageOps.autocontrast(
            img.convert("L")
        )

        return pytesseract.image_to_string(
            img,
            lang=use_lang,
            config="--psm 6",
        ).strip()

    except Exception:
        return ""



def embedded_text(page: fitz.Page) -> str:
    return _embedded_text(page)


def ocr_page_fast(page: fitz.Page, lang: str) -> str:
    return _ocr_page_fast(page, lang)


def ocr_page_full(page: fitz.Page, lang: str) -> str:
    return _ocr_page_full(page, lang)