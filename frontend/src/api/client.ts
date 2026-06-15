import type {
  ClassifyResponse,
  GeneratePayload,
  GenerateResponse,
  Kind,
  ProjectCreated,
  UploadResponse,
} from "../types/pdf";

const BASE = "/api/projects";

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  async createProject(): Promise<ProjectCreated> {
    return asJson(await fetch(BASE, { method: "POST" }));
  },

  async upload(projectId: string, kind: Kind, file: File): Promise<UploadResponse> {
    const form = new FormData();
    form.append("file", file);
    return asJson(
      await fetch(`${BASE}/${projectId}/upload/${kind}`, {
        method: "POST",
        body: form,
      })
    );
  },

  thumbnailUrl(projectId: string, kind: Kind, page: number): string {
    return `${BASE}/${projectId}/pdf/${kind}/page/${page}/thumbnail`;
  },

  fileUrl(projectId: string, kind: Kind): string {
    return `${BASE}/${projectId}/pdf/${kind}/file`;
  },

  async classify(projectId: string): Promise<ClassifyResponse> {
    return asJson(await fetch(`${BASE}/${projectId}/classify`, { method: "POST" }));
  },

  async generate(projectId: string, payload: GeneratePayload): Promise<GenerateResponse> {
    return asJson(
      await fetch(`${BASE}/${projectId}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },

  downloadUrl(projectId: string): string {
    return `${BASE}/${projectId}/download`;
  },

  async deleteProject(projectId: string): Promise<void> {
    const res = await fetch(`${BASE}/${projectId}`, { method: "DELETE" });
    if (!res.ok && res.status !== 404) throw new Error("Failed to delete project.");
  },
};
