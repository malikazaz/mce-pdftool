"""Pure PDF logic — no FastAPI / HTTP concerns here so it is trivially testable.

The assembly model reflects the MedConnect workflow:

Each output (Diploma = academic bucket, Continuation = "other" bucket) is built
in this exact order::

    1. Translated solicitor      (translated PDF)
    2. Translated apostille       (translated PDF)
    3. Translated bucket docs     (translated PDF, natural order)
    4. Notary stamp               (translated PDF, translated-only)
    5. English solicitor          (original PDF)
    6. English apostille          (original PDF)
    7. English bucket docs        (original PDF, natural order)

i.e. the whole translated section first (ending with the notary), then the whole
English section.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

Source = Literal["original", "translated"]


class PdfValidationError(Exception):
    """Raised when an uploaded file is not a usable PDF."""


class PageSelectionError(Exception):
    """Raised when a requested page does not exist in its source PDF."""


@dataclass(frozen=True)
class PageRef:
    """A single page to place in an output: which PDF, which 1-based page."""

    source: Source
    page: int  # 1-based


def validate_pdf(path: str | Path) -> int:
    """Validate that ``path`` is a readable, non-empty, unencrypted PDF.

    Returns the page count. Raises :class:`PdfValidationError` otherwise. Error
    messages never include document contents.
    """
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            # Try empty-password decrypt; many scans are flagged but openable.
            if reader.decrypt("") == 0:  # 0 == failure
                raise PdfValidationError("PDF is password protected and cannot be read.")
        count = len(reader.pages)
    except PdfValidationError:
        raise
    except (PyPdfError, OSError, ValueError) as exc:
        raise PdfValidationError("File is not a valid or readable PDF.") from exc

    if count == 0:
        raise PdfValidationError("PDF contains no pages.")
    return count


def validate_selection(page_count: int, pages: list[int], source_name: str) -> None:
    """Ensure every page number is a valid 1-based index within ``page_count``."""
    for p in pages:
        if not isinstance(p, int) or p < 1 or p > page_count:
            raise PageSelectionError(
                f"Page {p} is out of range for the {source_name} PDF "
                f"(which has {page_count} page(s))."
            )


def render_thumbnail(path: str | Path, page_1based: int, width: int) -> bytes:
    """Render a single page to PNG bytes at the requested pixel width."""
    doc = fitz.open(str(path))
    try:
        if page_1based < 1 or page_1based > doc.page_count:
            raise PageSelectionError(
                f"Page {page_1based} is out of range (PDF has {doc.page_count} page(s))."
            )
        page = doc.load_page(page_1based - 1)
        # Scale so the rendered width matches `width` px.
        zoom = width / page.rect.width if page.rect.width else 1.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes("png")
    finally:
        doc.close()


def assemble_output(
    readers: dict[Source, PdfReader],
    ordered_refs: list[PageRef],
    dest_path: str | Path,
) -> int:
    """Write the pages in ``ordered_refs`` to ``dest_path`` in exactly that order.

    ``readers`` maps each source to an open :class:`PdfReader`. Returns the number
    of pages written. This is the generic primitive; ordering decisions live in
    :func:`build_two_outputs`.
    """
    writer = PdfWriter()
    for ref in ordered_refs:
        reader = readers[ref.source]
        count = len(reader.pages)
        validate_selection(count, [ref.page], ref.source)
        writer.add_page(reader.pages[ref.page - 1])  # 1-based -> 0-based

    with open(dest_path, "wb") as fh:
        writer.write(fh)
    return len(ordered_refs)


# --- Higher-level composition --------------------------------------------------


@dataclass
class LegalPages:
    """The three legal pages, by source. Notary is translated-only."""

    solicitor_original: list[int]
    solicitor_translated: list[int]
    apostille_original: list[int]
    apostille_translated: list[int]
    notary_translated: list[int]


def build_ordered_refs(
    legal: LegalPages,
    bucket_original: list[int],
    bucket_translated: list[int],
) -> list[PageRef]:
    """Construct the ordered page list for one output following the spec order."""
    refs: list[PageRef] = []

    # --- Translated section ---
    refs += [PageRef("translated", p) for p in legal.solicitor_translated]
    refs += [PageRef("translated", p) for p in legal.apostille_translated]
    refs += [PageRef("translated", p) for p in bucket_translated]
    refs += [PageRef("translated", p) for p in legal.notary_translated]

    # --- English / original section (no notary) ---
    refs += [PageRef("original", p) for p in legal.solicitor_original]
    refs += [PageRef("original", p) for p in legal.apostille_original]
    refs += [PageRef("original", p) for p in bucket_original]

    return refs


@dataclass
class OutputResult:
    filename: str
    page_count: int
    path: str


def build_two_outputs(
    original_path: str | Path,
    translated_path: str | Path,
    legal: LegalPages,
    academic_original: list[int],
    academic_translated: list[int],
    other_original: list[int],
    other_translated: list[int],
    diploma_filename: str,
    continuation_filename: str,
    output_dir: str | Path,
) -> list[OutputResult]:
    """Build both the Diploma and Continuation PDFs and return their metadata."""
    readers: dict[Source, PdfReader] = {
        "original": PdfReader(str(original_path)),
        "translated": PdfReader(str(translated_path)),
    }
    output_dir = Path(output_dir)

    plans = [
        (diploma_filename, academic_original, academic_translated),
        (continuation_filename, other_original, other_translated),
    ]

    results: list[OutputResult] = []
    for filename, bucket_orig, bucket_trans in plans:
        refs = build_ordered_refs(legal, bucket_orig, bucket_trans)
        dest = output_dir / filename
        page_count = assemble_output(readers, refs, dest)
        results.append(OutputResult(filename=filename, page_count=page_count, path=str(dest)))

    return results
