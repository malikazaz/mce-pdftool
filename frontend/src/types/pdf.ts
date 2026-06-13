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
