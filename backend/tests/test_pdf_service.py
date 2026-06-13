"""Unit tests for the pure PDF logic."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from app import pdf_service
from app.pdf_service import (
    LegalPages,
    PageSelectionError,
    PdfValidationError,
)

from .conftest import make_pdf, page_marker


def _markers(path: str | Path) -> list[str]:
    reader = PdfReader(str(path))
    return [page_marker(reader, i) for i in range(len(reader.pages))]


def test_validate_pdf_counts_pages(sample_pdfs):
    assert pdf_service.validate_pdf(sample_pdfs["original"]) == 5
    assert pdf_service.validate_pdf(sample_pdfs["translated"]) == 6


def test_validate_pdf_rejects_non_pdf(tmp_path):
    bad = tmp_path / "not.pdf"
    bad.write_text("this is not a pdf")
    with pytest.raises(PdfValidationError):
        pdf_service.validate_pdf(bad)


def test_validate_selection_rejects_out_of_range():
    with pytest.raises(PageSelectionError):
        pdf_service.validate_selection(3, [4], "original")
    with pytest.raises(PageSelectionError):
        pdf_service.validate_selection(3, [0], "original")


def _legal() -> LegalPages:
    return LegalPages(
        solicitor_original=[1],
        solicitor_translated=[1],
        apostille_original=[2],
        apostille_translated=[2],
        notary_translated=[6],
    )


def test_diploma_order_translated_first_then_notary_then_english(sample_pdfs, tmp_path):
    results = pdf_service.build_two_outputs(
        original_path=sample_pdfs["original"],
        translated_path=sample_pdfs["translated"],
        legal=_legal(),
        academic_original=[3, 5],
        academic_translated=[3, 5],
        other_original=[4],
        other_translated=[4],
        diploma_filename="Diploma.pdf",
        continuation_filename="Continuation.pdf",
        output_dir=tmp_path,
    )

    diploma = next(r for r in results if r.filename == "Diploma.pdf")
    assert diploma.page_count == 9
    # Exact spec order: translated section (ends with notary), then English section.
    assert _markers(diploma.path) == [
        "TR-SOL",
        "TR-APO",
        "TR-ACAD1",
        "TR-ACAD2",
        "TR-NOTARY",
        "ORIG-SOL",
        "ORIG-APO",
        "ORIG-ACAD1",
        "ORIG-ACAD2",
    ]


def test_continuation_contains_only_other_bucket(sample_pdfs, tmp_path):
    results = pdf_service.build_two_outputs(
        original_path=sample_pdfs["original"],
        translated_path=sample_pdfs["translated"],
        legal=_legal(),
        academic_original=[3, 5],
        academic_translated=[3, 5],
        other_original=[4],
        other_translated=[4],
        diploma_filename="Diploma.pdf",
        continuation_filename="Continuation.pdf",
        output_dir=tmp_path,
    )
    cont = next(r for r in results if r.filename == "Continuation.pdf")
    assert _markers(cont.path) == [
        "TR-SOL",
        "TR-APO",
        "TR-OTHER1",
        "TR-NOTARY",
        "ORIG-SOL",
        "ORIG-APO",
        "ORIG-OTHER1",
    ]
    # No notary appears in the English section.
    assert _markers(cont.path).count("TR-NOTARY") == 1


def test_no_notary_in_english_section(sample_pdfs, tmp_path):
    # Legal with no notary configured -> output has no notary page at all.
    legal = LegalPages(
        solicitor_original=[1],
        solicitor_translated=[1],
        apostille_original=[2],
        apostille_translated=[2],
        notary_translated=[],
    )
    results = pdf_service.build_two_outputs(
        original_path=sample_pdfs["original"],
        translated_path=sample_pdfs["translated"],
        legal=legal,
        academic_original=[3],
        academic_translated=[3],
        other_original=[],
        other_translated=[],
        diploma_filename="D.pdf",
        continuation_filename="C.pdf",
        output_dir=tmp_path,
    )
    diploma = next(r for r in results if r.filename == "D.pdf")
    assert "TR-NOTARY" not in _markers(diploma.path)


def test_multi_page_legal_pages_counted(sample_pdfs, tmp_path):
    legal = LegalPages(
        solicitor_original=[1, 2],  # pretend two-page solicitor
        solicitor_translated=[1, 2],
        apostille_original=[],
        apostille_translated=[],
        notary_translated=[6],
    )
    results = pdf_service.build_two_outputs(
        original_path=sample_pdfs["original"],
        translated_path=sample_pdfs["translated"],
        legal=legal,
        academic_original=[3],
        academic_translated=[3],
        other_original=[],
        other_translated=[],
        diploma_filename="D.pdf",
        continuation_filename="C.pdf",
        output_dir=tmp_path,
    )
    diploma = next(r for r in results if r.filename == "D.pdf")
    # translated: 2 sol + 1 acad + 1 notary = 4 ; english: 2 sol + 1 acad = 3
    assert diploma.page_count == 7


def test_assemble_output_rejects_invalid_page(sample_pdfs, tmp_path):
    readers = {
        "original": PdfReader(str(sample_pdfs["original"])),
        "translated": PdfReader(str(sample_pdfs["translated"])),
    }
    with pytest.raises(PageSelectionError):
        pdf_service.assemble_output(
            readers, [pdf_service.PageRef("original", 99)], tmp_path / "x.pdf"
        )


def test_render_thumbnail_returns_png(sample_pdfs):
    png = pdf_service.render_thumbnail(sample_pdfs["original"], 1, 200)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
