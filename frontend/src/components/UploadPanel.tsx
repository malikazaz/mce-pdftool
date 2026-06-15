import { useState } from "react";
import { api } from "../api/client";
import type { Kind } from "../types/pdf";

interface Props {
  projectId: string;
  pageCounts: { original: number | null; translated: number | null };
  onUploaded: (kind: Kind, pageCount: number, warning: string | null) => void;
  onError: (message: string) => void;
}

function Dropzone({
  kind,
  pageCount,
  onFile,
}: {
  kind: Kind;
  pageCount: number | null;
  onFile: (file: File, onProgress: (percent: number) => void) => Promise<void>;
}) {
  const [dragover, setDragover] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);

  const handle = async (file: File | undefined) => {
    if (!file) return;
    setProgress(0);
    setBusy(true);
    await onFile(file, setProgress);
    setBusy(false);
  };

  const title = kind === "original" ? "Original / English PDF" : "Translated PDF";

  return (
    <label
      className={`dropzone ${dragover ? "dragover" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragover(true);
      }}
      onDragLeave={() => setDragover(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragover(false);
        void handle(e.dataTransfer.files[0]);
      }}
    >
      <strong>{title}</strong>
      <input
        type="file"
        accept="application/pdf"
        style={{ display: "none" }}
        onChange={(e) => void handle(e.target.files?.[0])}
      />
      {busy ? (
        <div className="upload-progress">
          <div className="meta">Uploading… {progress}%</div>
          <div className="progress">
            <div className="progress-bar" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : (
        <div className="meta">
          {pageCount !== null
            ? `Uploaded — ${pageCount} page(s). Click to replace.`
            : "Drag & drop or click to choose a PDF"}
        </div>
      )}
    </label>
  );
}

export default function UploadPanel({ projectId, pageCounts, onUploaded, onError }: Props) {
  const upload = async (
    kind: Kind,
    file: File,
    onProgress: (percent: number) => void
  ) => {
    try {
      const res = await api.upload(projectId, kind, file, onProgress);
      onUploaded(kind, res.page_count, res.warning);
    } catch (e) {
      onError((e as Error).message);
    }
  };

  return (
    <section className="panel">
      <h2>1. Upload documents</h2>
      <div className="row">
        <Dropzone
          kind="original"
          pageCount={pageCounts.original}
          onFile={(f, onProgress) => upload("original", f, onProgress)}
        />
        <Dropzone
          kind="translated"
          pageCount={pageCounts.translated}
          onFile={(f, onProgress) => upload("translated", f, onProgress)}
        />
      </div>
    </section>
  );
}
