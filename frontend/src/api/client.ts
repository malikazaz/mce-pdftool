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

  upload(
    projectId: string,
    kind: Kind,
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<UploadResponse> {
    // XMLHttpRequest (not fetch) so we get real upload progress events for the % bar.
    return new Promise<UploadResponse>((resolve, reject) => {
      const form = new FormData();
      form.append("file", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${BASE}/${projectId}/upload/${kind}`);

      xhr.upload.onprogress = (e) => {
        if (onProgress && e.lengthComputable) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      xhr.onload = () => {
        // Mirror asJson(): on non-2xx, surface the backend's `detail` if present.
        let body: unknown = undefined;
        try {
          body = JSON.parse(xhr.responseText);
        } catch {
          /* non-JSON body */
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body as UploadResponse);
        } else {
          const detail =
            (body as { detail?: unknown } | undefined)?.detail ?? xhr.statusText;
          reject(new Error(typeof detail === "string" ? detail : JSON.stringify(detail)));
        }
      };
      xhr.onerror = () => reject(new Error("Upload failed — network error."));
      xhr.send(form);
    });
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
