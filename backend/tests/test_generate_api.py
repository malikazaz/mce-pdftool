"""End-to-end API tests using FastAPI's TestClient."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from .conftest import make_pdf


@pytest.fixture
def client(isolated_data_dir):
    # Import after the data dir env var is set so settings pick it up.
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def _upload_pair(client, sample_pdfs) -> str:
    pid = client.post("/api/projects").json()["project_id"]
    with open(sample_pdfs["original"], "rb") as f:
        r = client.post(
            f"/api/projects/{pid}/upload/original",
            files={"file": ("original.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200
    with open(sample_pdfs["translated"], "rb") as f:
        r = client.post(
            f"/api/projects/{pid}/upload/translated",
            files={"file": ("translated.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200
    return pid


def _payload() -> dict:
    return {
        "client_name": "John Smith",
        "labels": {"diploma": "Diploma", "continuation": "Continuation"},
        "legal_pages": {
            "solicitor": {"original": [1], "translated": [1]},
            "apostille": {"original": [2], "translated": [2]},
            "notary": {"translated": [6]},
        },
        "academic": {"original": [3, 5], "translated": [3, 5]},
        "other": {"original": [4], "translated": [4]},
    }


def test_happy_path_generate_and_download(client, sample_pdfs):
    pid = _upload_pair(client, sample_pdfs)

    r = client.post(f"/api/projects/{pid}/generate", json=_payload())
    assert r.status_code == 200, r.text
    body = r.json()
    names = {o["filename"] for o in body["outputs"]}
    assert names == {"John Smith - Diploma.pdf", "John Smith - Continuation.pdf"}
    diploma = next(o for o in body["outputs"] if "Diploma" in o["filename"])
    assert diploma["page_count"] == 9

    dl = client.get(f"/api/projects/{pid}/download")
    assert dl.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(dl.content))
    assert set(zf.namelist()) == names


def test_upload_rejects_non_pdf(client, tmp_path):
    pid = client.post("/api/projects").json()["project_id"]
    bad = tmp_path / "bad.pdf"
    bad.write_text("not a pdf")
    with open(bad, "rb") as f:
        r = client.post(
            f"/api/projects/{pid}/upload/original",
            files={"file": ("bad.pdf", f, "application/pdf")},
        )
    assert r.status_code == 400


def test_mismatched_counts_warn_not_block(client, sample_pdfs):
    # Original 5 pages, translated 6 pages -> warning on translated upload.
    pid = client.post("/api/projects").json()["project_id"]
    with open(sample_pdfs["original"], "rb") as f:
        client.post(
            f"/api/projects/{pid}/upload/original",
            files={"file": ("o.pdf", f, "application/pdf")},
        )
    with open(sample_pdfs["translated"], "rb") as f:
        r = client.post(
            f"/api/projects/{pid}/upload/translated",
            files={"file": ("t.pdf", f, "application/pdf")},
        )
    assert r.status_code == 200
    assert r.json()["warning"] is not None


def test_generate_rejects_out_of_range_page(client, sample_pdfs):
    pid = _upload_pair(client, sample_pdfs)
    payload = _payload()
    payload["academic"]["original"] = [99]
    r = client.post(f"/api/projects/{pid}/generate", json=payload)
    assert r.status_code == 400


def test_generate_requires_client_name(client, sample_pdfs):
    pid = _upload_pair(client, sample_pdfs)
    payload = _payload()
    payload["client_name"] = "   "
    r = client.post(f"/api/projects/{pid}/generate", json=payload)
    assert r.status_code == 422


def test_filename_sanitised_against_traversal(client, sample_pdfs):
    pid = _upload_pair(client, sample_pdfs)
    payload = _payload()
    payload["client_name"] = "../../etc/passwd"
    r = client.post(f"/api/projects/{pid}/generate", json=payload)
    assert r.status_code == 200
    for o in r.json()["outputs"]:
        assert "/" not in o["filename"] and "\\" not in o["filename"]
        assert ".." not in o["filename"]


def test_delete_project_removes_files(client, sample_pdfs):
    pid = _upload_pair(client, sample_pdfs)
    client.post(f"/api/projects/{pid}/generate", json=_payload())
    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204
    assert client.get(f"/api/projects/{pid}/download").status_code == 404
