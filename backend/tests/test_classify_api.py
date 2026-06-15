"""API tests for the /classify endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from .conftest import make_text_pdf


@pytest.fixture
def client(isolated_data_dir):
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def classifiable_pair(tmp_path):
    original = tmp_path / "original.pdf"
    translated = tmp_path / "translated.pdf"
    make_text_pdf(
        original,
        [
            "Solicitor certification.",
            "Apostille.",
            "Statement of Results. Cambridge Assessment. Candidate Number 1. Biology: A",
            "To whom it may concern. I confirm grades. Yours sincerely.",
        ],
    )
    make_text_pdf(
        translated,
        ["Заверен превод.", "Апостил.", "Диплома, академична справка", "Пълномощно.", "Нотариус."],
    )
    return original, translated


def _upload_pair(client, original, translated) -> str:
    pid = client.post("/api/projects").json()["project_id"]
    with open(original, "rb") as f:
        client.post(f"/api/projects/{pid}/upload/original", files={"file": ("o.pdf", f, "application/pdf")})
    with open(translated, "rb") as f:
        client.post(f"/api/projects/{pid}/upload/translated", files={"file": ("t.pdf", f, "application/pdf")})
    return pid


def test_classify_requires_both_pdfs(client):
    pid = client.post("/api/projects").json()["project_id"]
    r = client.post(f"/api/projects/{pid}/classify")
    assert r.status_code == 400


def test_classify_returns_shape(client, classifiable_pair):
    pid = _upload_pair(client, *classifiable_pair)
    r = client.post(f"/api/projects/{pid}/classify")
    assert r.status_code == 200
    body = r.json()
    assert "ocr_available" in body and "suggestions" in body

    if not body["ocr_available"]:
        # No Tesseract on this machine: feature degrades, manual labelling still works.
        assert body["note"]
        return

    # With OCR available, suggestions cover document pages only (legal pages excluded).
    keys = {(s["kind"], s["page"]) for s in body["suggestions"]}
    assert ("original", 1) not in keys and ("original", 2) not in keys
    assert ("translated", 1) not in keys
    # The Cambridge statement-of-results page should be academic.
    orig3 = next(s for s in body["suggestions"] if s["kind"] == "original" and s["page"] == 3)
    assert orig3["suggested_role"] == "academic"
