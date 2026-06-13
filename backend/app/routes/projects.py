"""All ``/api/projects`` endpoints.

PORTAL-AUTH: When embedded in the MedConnect portal, protect this whole router
with the portal's auth/session dependency, e.g.::

    router = APIRouter(..., dependencies=[Depends(require_portal_user)])

and scope project ownership to the authenticated user.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse

from .. import db, pdf_service, storage_service, zip_service
from ..config import get_settings
from ..models import (
    GenerateRequest,
    GenerateResponse,
    OutputSummary,
    ProjectCreatedResponse,
    UploadResponse,
)
from ..pdf_service import (
    LegalPages,
    PageSelectionError,
    PdfValidationError,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])

Kind = Literal["original", "translated"]


def _require_project(project_id: str) -> dict:
    project = db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.post("", response_model=ProjectCreatedResponse, status_code=201)
def create_project() -> ProjectCreatedResponse:
    project_id = uuid.uuid4().hex
    root = storage_service.ensure_project_dirs(project_id)
    record = db.create_project(project_id, output_dir=str(root))
    return ProjectCreatedResponse(
        project_id=record["project_id"],
        created_at=record["created_at"],
        status=record["status"],
    )


async def _save_upload(project: dict, kind: Kind, file: UploadFile) -> UploadResponse:
    settings = get_settings()

    if file.content_type not in ("application/pdf", "application/octet-stream") and not (
        file.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    project_id = project["project_id"]
    dest = storage_service.safe_join(
        storage_service.project_dir(project_id), f"{kind}.pdf"
    )

    # Stream to disk with a hard size cap (reject before reading the whole file).
    size = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds the {settings.max_upload_mb} MB limit.",
                )
            out.write(chunk)

    try:
        page_count = pdf_service.validate_pdf(dest)
    except PdfValidationError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    field = "original_page_count" if kind == "original" else "translated_page_count"
    path_field = "original_pdf_path" if kind == "original" else "translated_pdf_path"
    db.update_project(project_id, **{field: page_count, path_field: str(dest)})

    # Recompute status now that this file is in place.
    refreshed = db.get_project(project_id)
    both = bool(refreshed["original_pdf_path"]) and bool(refreshed["translated_pdf_path"])
    db.update_project(
        project_id, status="both_uploaded" if both else f"{kind}_uploaded"
    )

    warning = None
    if both:
        oc = refreshed["original_page_count"]
        tc = refreshed["translated_page_count"]
        if oc != tc:
            warning = (
                f"Original has {oc} page(s) and translated has {tc}. "
                "This is expected if the translated set includes a notary page, "
                "but please double-check the page labelling."
            )

    return UploadResponse(kind=kind, page_count=page_count, warning=warning)


@router.post("/{project_id}/upload/original", response_model=UploadResponse)
async def upload_original(project_id: str, file: UploadFile) -> UploadResponse:
    project = _require_project(project_id)
    return await _save_upload(project, "original", file)


@router.post("/{project_id}/upload/translated", response_model=UploadResponse)
async def upload_translated(project_id: str, file: UploadFile) -> UploadResponse:
    project = _require_project(project_id)
    return await _save_upload(project, "translated", file)


@router.get("/{project_id}/pdf/{kind}/page/{page_number}/thumbnail")
def page_thumbnail(project_id: str, kind: Kind, page_number: int) -> Response:
    project = _require_project(project_id)
    path = project["original_pdf_path"] if kind == "original" else project["translated_pdf_path"]
    if not path:
        raise HTTPException(status_code=404, detail=f"No {kind} PDF uploaded yet.")
    try:
        png = pdf_service.render_thumbnail(
            path, page_number, get_settings().thumbnail_width
        )
    except PageSelectionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png")


@router.get("/{project_id}/pdf/{kind}/file")
def pdf_file(project_id: str, kind: Kind) -> FileResponse:
    project = _require_project(project_id)
    path = project["original_pdf_path"] if kind == "original" else project["translated_pdf_path"]
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail=f"No {kind} PDF uploaded yet.")
    return FileResponse(path, media_type="application/pdf")


@router.post("/{project_id}/generate", response_model=GenerateResponse)
def generate(project_id: str, payload: GenerateRequest) -> GenerateResponse:
    project = _require_project(project_id)
    original_path = project["original_pdf_path"]
    translated_path = project["translated_pdf_path"]
    if not original_path or not translated_path:
        raise HTTPException(
            status_code=400, detail="Both original and translated PDFs must be uploaded."
        )

    oc = project["original_page_count"]
    tc = project["translated_page_count"]

    lp = payload.legal_pages
    legal = LegalPages(
        solicitor_original=lp.solicitor.original,
        solicitor_translated=lp.solicitor.translated,
        apostille_original=lp.apostille.original,
        apostille_translated=lp.apostille.translated,
        notary_translated=lp.notary.translated,
    )

    # Validate every referenced page against the correct source PDF.
    original_pages = (
        legal.solicitor_original
        + legal.apostille_original
        + payload.academic.original
        + payload.other.original
    )
    translated_pages = (
        legal.solicitor_translated
        + legal.apostille_translated
        + legal.notary_translated
        + payload.academic.translated
        + payload.other.translated
    )
    try:
        pdf_service.validate_selection(oc, original_pages, "original")
        pdf_service.validate_selection(tc, translated_pages, "translated")
    except PageSelectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    warnings: list[str] = []
    if not (payload.academic.original or payload.academic.translated):
        warnings.append("The Diploma output has no academic documents selected.")
    if not (payload.other.original or payload.other.translated):
        warnings.append("The Continuation output has no other documents selected.")

    # Build sanitised, de-duplicated output filenames.
    diploma_name = storage_service.sanitise_filename(
        f"{payload.client_name} - {payload.labels.diploma}", default_stem="Diploma"
    )
    continuation_name = storage_service.sanitise_filename(
        f"{payload.client_name} - {payload.labels.continuation}",
        default_stem="Continuation",
    )
    if diploma_name.lower() == continuation_name.lower():
        raise HTTPException(
            status_code=400,
            detail="The two output documents must have different names.",
        )

    output_dir = storage_service.safe_join(
        storage_service.project_dir(project_id), "outputs"
    )
    # Clear any prior generation so the ZIP only contains the current outputs.
    for old in output_dir.glob("*"):
        old.unlink()

    results = pdf_service.build_two_outputs(
        original_path=original_path,
        translated_path=translated_path,
        legal=legal,
        academic_original=payload.academic.original,
        academic_translated=payload.academic.translated,
        other_original=payload.other.original,
        other_translated=payload.other.translated,
        diploma_filename=diploma_name,
        continuation_filename=continuation_name,
        output_dir=output_dir,
    )

    zip_path = storage_service.safe_join(
        storage_service.project_dir(project_id), "output.zip"
    )
    zip_service.build_zip([r.path for r in results], zip_path)
    db.update_project(project_id, status="generated")

    return GenerateResponse(
        outputs=[OutputSummary(filename=r.filename, page_count=r.page_count) for r in results],
        download_url=f"/api/projects/{project_id}/download",
        warnings=warnings,
    )


@router.get("/{project_id}/download")
def download(project_id: str) -> FileResponse:
    _require_project(project_id)
    zip_path = storage_service.safe_join(
        storage_service.project_dir(project_id), "output.zip"
    )
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Nothing generated yet.")
    return FileResponse(
        zip_path, media_type="application/zip", filename="medconnect-documents.zip"
    )


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str) -> Response:
    _require_project(project_id)
    storage_service.remove_project_dir(project_id)
    db.delete_project(project_id)
    return Response(status_code=204)
