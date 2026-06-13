"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


# --- Responses ---------------------------------------------------------------


class ProjectCreatedResponse(BaseModel):
    project_id: str
    created_at: str
    status: str


class UploadResponse(BaseModel):
    kind: str  # "original" | "translated"
    page_count: int
    # Non-blocking warning, e.g. when original/translated page counts differ.
    warning: str | None = None


class OutputSummary(BaseModel):
    filename: str
    page_count: int


class GenerateResponse(BaseModel):
    outputs: list[OutputSummary]
    download_url: str
    warnings: list[str] = Field(default_factory=list)


# --- Generate request --------------------------------------------------------


class LegalPageSelection(BaseModel):
    """Pages for solicitor/apostille (present in both PDFs)."""

    original: list[int] = Field(default_factory=list)
    translated: list[int] = Field(default_factory=list)


class NotarySelection(BaseModel):
    """Notary pages exist only in the translated PDF."""

    translated: list[int] = Field(default_factory=list)


class LegalPagesPayload(BaseModel):
    solicitor: LegalPageSelection = Field(default_factory=LegalPageSelection)
    apostille: LegalPageSelection = Field(default_factory=LegalPageSelection)
    notary: NotarySelection = Field(default_factory=NotarySelection)


class BucketSelection(BaseModel):
    """Document pages for a bucket (academic or other), per source PDF."""

    original: list[int] = Field(default_factory=list)
    translated: list[int] = Field(default_factory=list)


class OutputLabels(BaseModel):
    diploma: str = "Diploma"
    continuation: str = "Continuation"


class GenerateRequest(BaseModel):
    client_name: str = Field(min_length=1, max_length=200)
    labels: OutputLabels = Field(default_factory=OutputLabels)
    legal_pages: LegalPagesPayload = Field(default_factory=LegalPagesPayload)
    academic: BucketSelection = Field(default_factory=BucketSelection)
    other: BucketSelection = Field(default_factory=BucketSelection)

    @field_validator("client_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("client_name must not be empty.")
        return v
