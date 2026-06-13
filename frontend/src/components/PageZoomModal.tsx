import { useEffect, useRef } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { api } from "../api/client";
import type { Kind } from "../types/pdf";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

interface Props {
  projectId: string;
  kind: Kind;
  page: number;
  onClose: () => void;
}

// Full-page zoom rendered client-side with PDF.js for close inspection.
export default function PageZoomModal({ projectId, kind, page, onClose }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let cancelled = false;
    let task: pdfjsLib.PDFDocumentLoadingTask | null = null;

    (async () => {
      task = pdfjsLib.getDocument(api.fileUrl(projectId, kind));
      const doc = await task.promise;
      if (cancelled) return;
      const pdfPage = await doc.getPage(page);
      const viewport = pdfPage.getViewport({ scale: 1.5 });
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d")!;
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await pdfPage.render({ canvasContext: ctx, viewport }).promise;
    })().catch(() => {
      /* ignore render errors on close/navigation */
    });

    return () => {
      cancelled = true;
      task?.destroy();
    };
  }, [projectId, kind, page]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <strong>
            {kind === "original" ? "Original" : "Translated"} — page {page}
          </strong>
          <button className="secondary" onClick={onClose}>
            Close
          </button>
        </div>
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}
