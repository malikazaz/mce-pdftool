// Types mirroring the backend Pydantic models.

export type Kind = "original" | "translated";

// Per-page role. `notary` is only valid on the translated PDF.
export type Role =
  | "unassigned"
  | "solicitor"
  | "apostille"
  | "notary"
  | "academic"
  | "other";

export interface ProjectCreated {
  project_id: string;
  created_at: string;
  status: string;
}

export interface UploadResponse {
  kind: Kind;
  page_count: number;
  warning: string | null;
}

export interface OutputSummary {
  filename: string;
  page_count: number;
}

export interface GenerateResponse {
  outputs: OutputSummary[];
  download_url: string;
  warnings: string[];
}

export interface LegalPageSelection {
  original: number[];
  translated: number[];
}

export interface GeneratePayload {
  client_name: string;
  labels: { diploma: string; continuation: string };
  legal_pages: {
    solicitor: LegalPageSelection;
    apostille: LegalPageSelection;
    notary: { translated: number[] };
  };
  academic: LegalPageSelection;
  other: LegalPageSelection;
}

// Classification map: per kind, page number (1-based) -> role.
export type Classification = Record<Kind, Record<number, Role>>;

// --- Auto-classification (local OCR + rules) ---

export interface PageSuggestion {
  kind: Kind;
  page: number;
  suggested_role: "academic" | "other";
  confidence: number;
  needs_review: boolean;
  signals: string[];
}

export interface ClassifyResponse {
  ocr_available: boolean;
  suggestions: PageSuggestion[];
  note: string | null;
}

// Per-page metadata about a suggestion, so the UI can flag pages to review.
export interface SuggestionInfo {
  needsReview: boolean;
  confidence: number;
}
export type SuggestionMeta = Record<Kind, Record<number, SuggestionInfo>>;
